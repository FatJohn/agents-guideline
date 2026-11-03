plugins { id("com.android.library") }

android {
    namespace = "com.example.sdk"
    lint {
        warningsAsErrors = true
        abortOnError = true
        // 版本更新交給 dependabot
        disable += setOf("GradleDependency", "NewerVersionAvailable")
        enable += setOf("StopShip")
    }
}
