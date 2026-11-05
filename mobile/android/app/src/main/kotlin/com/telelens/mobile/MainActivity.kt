package com.telelens.mobile

import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import androidx.annotation.NonNull
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.telelens.mobile/hardware"
    private var torchEnabled = false

    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "setTorch" -> {
                    val enabled = call.argument<Boolean>("enabled") ?: false
                    val success = setTorchState(enabled)
                    result.success(success)
                }
                "isTorchAvailable" -> {
                    result.success(isTorchAvailable())
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun isTorchAvailable(): Boolean {
        val cameraManager = getSystemService(Context.CAMERA_SERVICE) as? CameraManager ?: return false
        try {
            for (id in cameraManager.cameraIdList) {
                val chars = cameraManager.getCameraCharacteristics(id)
                val hasFlash = chars.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) ?: false
                if (hasFlash) return true
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return false
    }

    private fun setTorchState(enabled: Boolean): Boolean {
        val cameraManager = getSystemService(Context.CAMERA_SERVICE) as? CameraManager ?: return false
        try {
            // Prefer rear camera with flash
            for (id in cameraManager.cameraIdList) {
                val chars = cameraManager.getCameraCharacteristics(id)
                val hasFlash = chars.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) ?: false
                val facing = chars.get(CameraCharacteristics.LENS_FACING)
                if (hasFlash && facing == CameraCharacteristics.LENS_FACING_BACK) {
                    cameraManager.setTorchMode(id, enabled)
                    torchEnabled = enabled
                    return true
                }
            }
            // Fallback to any camera with flash
            for (id in cameraManager.cameraIdList) {
                val chars = cameraManager.getCameraCharacteristics(id)
                val hasFlash = chars.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) ?: false
                if (hasFlash) {
                    cameraManager.setTorchMode(id, enabled)
                    torchEnabled = enabled
                    return true
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return false
    }
}
