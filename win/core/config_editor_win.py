import re
from utils import logger_win

def get_param_value(content, section, param):
    """Ищет значение параметра в тексте конфига"""
    # Ищем блок [section] и внутри него параметр: значение
    pattern = rf"\[{section}\][^\[]*?{param}\s*:\s*([\d\.-]+)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1) if match else ""

def update_config_content(content, updates):
    """
    Обновляет содержимое файла.
    updates — это словарь: { "секция": {"параметр": "новое_значение"} }
    """
    new_content = content
    for section, params in updates.items():
        for param, new_val in params.items():
            # Находим нужную секцию и параметр, меняем только цифры
            pattern = rf"(\[{section}\][^\[]*?{param}\s*:\s*)([\d\.-]+)"
            if re.search(pattern, new_content, re.DOTALL):
                new_content = re.sub(pattern, rf"\1{new_val}", new_content, flags=re.DOTALL)
                logger_win.info(f"Обновлено: {section} -> {param} = {new_val}")
            else:
                logger_win.warning(f"Не найдено: {section} -> {param}")
    
    return new_content