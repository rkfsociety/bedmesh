package com.rkfsociety.bedmesh

import android.app.Application
import org.bouncycastle.jce.provider.BouncyCastleProvider
import java.security.Security

class BedMeshApp : Application() {
    override fun onCreate() {
        super.onCreate()
        installBouncyCastleForSshj()
    }

    private fun installBouncyCastleForSshj() {
        val name = BouncyCastleProvider.PROVIDER_NAME
        // В Android зарегистрирован урезанный провайдер "BC" без X25519 и др.; sshj падает на KEX.
        runCatching { Security.removeProvider(name) }
        runCatching { Security.insertProviderAt(BouncyCastleProvider(), 1) }
    }
}
