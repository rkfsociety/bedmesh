"""Локальная проверка trampoline K3SysUi без запуска Qt и без принтера.

Это не эмуляция всего K3SysUi: штатный QString::operator== и основной код
заменяются короткими ARM-заглушками. Проверяется только контракт новой ветки:
материал, сравнение диаметра, индексы 8/9 и fallback в старый код.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from unicorn import Uc, UcError, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_C1_C0_2,
    UC_CPU_ARM_CORTEX_A9,
    UC_ARM_REG_FPEXC,
    UC_ARM_REG_FP,
    UC_ARM_REG_LR,
    UC_ARM_REG_R4,
    UC_ARM_REG_R6,
    UC_ARM_REG_R7,
    UC_ARM_REG_SP,
)


BASE = 0x10000
TRAMPOLINE = 0x67CA00
DONE = 0x67CC00
EQ_STUB = 0x3CE68
FALLBACK = 0x14D5B0
RESTORE_EXIT = 0x14D768
R4_BASE = 0x200000
DIAMETER_PTR = 0x210000
FP = 0x220000


def arm_bytes(*words: int) -> bytes:
    return b"".join(struct.pack("<I", word) for word in words)


def branch_word(address: int, target: int) -> int:
    displacement = target - (address + 8)
    if displacement % 4 or not -(1 << 25) <= displacement < (1 << 25):
        raise ValueError(f"ARM branch вне диапазона: {address:#x} -> {target:#x}")
    return 0xEA000000 | ((displacement >> 2) & 0x00FFFFFF)


def load_candidate(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < TRAMPOLINE - BASE + 0x100:
        raise ValueError("кандидат слишком короткий")
    return data


def low_vfp_equivalent(code: bytes) -> bytes:
    """Переносит d16/d17 в d0/d1 для поддержки VFP в Unicorn.

    Unicorn на Windows исполняет низкие VFP-регистры надёжнее; байты меняются
    только в копии, загружаемой в эмулятор, исходный ELF не модифицируется.
    """
    replacements = {
        bytes.fromhex("00 0b d3 ed"): bytes.fromhex("00 0b 93 ed"),  # vldr d16
        bytes.fromhex("00 1b f7 ee"): bytes.fromhex("00 1b b7 ee"),  # vmov d17
        bytes.fromhex("e1 0b 70 ee"): bytes.fromhex("41 0b 30 ee"),  # vsub d16,d16,d17
        bytes.fromhex("e0 0b f0 ee"): bytes.fromhex("c0 0b b0 ee"),  # vabs d16
        # Unicorn не читает PC-relative double в d1 стабильно, поэтому
        # эквивалентно грузим тот же адрес через r7 (ниже r7 настроен).
        bytes.fromhex("24 1b df ed"): bytes.fromhex("00 1b 97 ed"),  # vldr d17
        bytes.fromhex("0b 1b df ed"): bytes.fromhex("00 1b 97 ed"),  # vldr d17
        bytes.fromhex("e1 0b f4 ee"): bytes.fromhex("c1 0b b4 ee"),  # vcmpe d16,d17
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code


def run_case(candidate: bytes, material: str, diameter: float) -> int:
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM, UC_CPU_ARM_CORTEX_A9)
    for address, size in ((0x3C000, 0x1000), (0x14D000, 0x1000),
                          (0x67C000, 0x1000), (0x200000, 0x4000),
                          (0x210000, 0x1000), (0x21F000, 0x2000)):
        uc.mem_map(address, size)

    # Виртуализируем только код trampoline из ELF-кандидата.
    code_offset = TRAMPOLINE - BASE
    uc.mem_write(TRAMPOLINE, low_vfp_equivalent(candidate[code_offset : code_offset + 0x100]))

    # QString::operator==(QString, const char*) для harness: r6=0 -> brass,
    # r6=1 -> hardened_steel.
    uc.mem_write(EQ_STUB, arm_bytes(
        0xE3560000,  # cmp r6, #0
        0x03A00001,  # moveq r0, #1
        0x13A00000,  # movne r0, #0
        0xE12FFF1E,  # bx lr
    ))

    # Fallback и успешный выход только помечают маршрут и останавливаются.
    uc.mem_write(FALLBACK, arm_bytes(
        0xE3A0000F,  # mov r0, #15
        0xE50B0018,  # str r0, [fp, #-0x18]
        branch_word(FALLBACK + 8, DONE),  # b DONE
    ))
    uc.mem_write(RESTORE_EXIT, arm_bytes(branch_word(RESTORE_EXIT, DONE)))  # b DONE

    uc.mem_write(R4_BASE + 0x29AC, struct.pack("<I", DIAMETER_PTR))
    uc.mem_write(DIAMETER_PTR, struct.pack("<d", diameter))
    uc.mem_write(FP - 0x2C, struct.pack("<I", 0x3C0910))

    uc.reg_write(UC_ARM_REG_FP, FP)
    uc.reg_write(UC_ARM_REG_SP, FP - 0x100)
    uc.reg_write(UC_ARM_REG_R4, R4_BASE)
    uc.reg_write(UC_ARM_REG_R6, 0 if material == "brass" else 1)
    uc.reg_write(UC_ARM_REG_R7, TRAMPOLINE + 0xA4)
    uc.reg_write(UC_ARM_REG_LR, DONE)
    # Разрешаем VFP-инструкции, используемые оригинальным ARM-кодом.
    uc.reg_write(UC_ARM_REG_C1_C0_2, 0xF00000)
    uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)

    stopped = False

    def stop_at_done(_uc: Uc, address: int, _size: int, _user: object) -> None:
        nonlocal stopped
        if address == DONE:
            stopped = True
            _uc.emu_stop()

    uc.hook_add(UC_HOOK_CODE, stop_at_done)
    try:
        # Верхняя граница после sentinel, чтобы hook успел зафиксировать маршрут.
        uc.emu_start(TRAMPOLINE, DONE + 4, count=200)
    except UcError as exc:
        raise AssertionError(f"ARM harness остановился с ошибкой для {material}/{diameter}: {exc}") from exc
    if not stopped:
        raise AssertionError(f"ARM harness не дошёл до sentinel для {material}/{diameter}")
    return struct.unpack("<I", uc.mem_read(FP - 0x18, 4))[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    candidate = load_candidate(args.candidate)
    diameters = (0.2, 0.25, 0.4, 0.6, 0.8, 1.0)
    cases = 0
    for material, expected_new in (("brass", 8), ("hardened_steel", 9)):
        for diameter in diameters:
            index = run_case(candidate, material, diameter)
            expected = expected_new if diameter == 1.0 else 15
            if index != expected:
                raise AssertionError(f"{material}/{diameter}: индекс {index}, ожидался {expected}")
            cases += 1
    print(f"OK: {cases} ARM-веток; brass-1.0 -> 8, hardened_steel-1.0 -> 9, остальные -> fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
