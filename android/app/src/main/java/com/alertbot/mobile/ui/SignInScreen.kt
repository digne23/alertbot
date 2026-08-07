package com.alertbot.mobile.ui

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.alertbot.mobile.R
import com.alertbot.mobile.data.ApiClient
import com.alertbot.mobile.data.displayName
import com.alertbot.mobile.data.isSignedIn
import com.alertbot.mobile.data.registerThisDevice
import com.alertbot.mobile.data.registrationKey
import com.alertbot.mobile.ui.components.BrandMark
import com.alertbot.mobile.ui.theme.BrandBlue
import com.alertbot.mobile.ui.theme.Critical
import com.alertbot.mobile.ui.theme.TextSecondary
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The whole of first-run setup. Two fields, one button.
 *
 * There is deliberately no server address, no username and no registration key
 * on this screen. The address is compiled in (`DEFAULT_SERVER_URL`) and the key
 * arrives from the server once the PIN is accepted — so the only things a
 * non-technical member of staff has to know are their own name and a PIN
 * someone told them.
 */
@Composable
fun SignInScreen(onSignedIn: (warningRes: Int?) -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var name by remember { mutableStateOf(context.displayName) }
    var pin by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    val unreachable = stringResource(R.string.error_unreachable)
    val wrongPin = stringResource(R.string.error_wrong_pin)
    val notConfigured = stringResource(R.string.error_not_configured)
    val needName = stringResource(R.string.error_no_name)
    val needPin = stringResource(R.string.error_no_pin)
    val tooManyFallback = stringResource(R.string.error_too_many)

    fun submit() {
        when {
            name.isBlank() -> { error = needName; return }
            pin.isBlank() -> { error = needPin; return }
        }

        busy = true
        error = null
        scope.launchSignIn(
            context = context,
            name = name.trim(),
            pin = pin,
            onFailure = { message ->
                busy = false
                error = message
            },
            onSuccess = { warningRes ->
                busy = false
                onSignedIn(warningRes)
            },
            unreachable = unreachable,
            wrongPin = wrongPin,
            notConfigured = notConfigured,
            tooManyFallback = tooManyFallback,
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .imePadding(),
    ) {
        // Brand header — the one place the blue takes the whole width.
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxWidth()
                .background(BrandBlue)
                .statusBarsPadding()
                .padding(top = 48.dp, bottom = 44.dp),
        ) {
            BrandMark(size = 84)
            Spacer(Modifier.height(20.dp))
            Text(
                text = stringResource(R.string.app_name),
                style = MaterialTheme.typography.displaySmall,
                color = Color.White,
            )
        }

        Column(
            modifier = Modifier
                .navigationBarsPadding()
                .padding(horizontal = 24.dp, vertical = 32.dp),
        ) {
            Text(
                text = stringResource(R.string.sign_in_title),
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.sign_in_subtitle),
                style = MaterialTheme.typography.bodyLarge,
                color = TextSecondary,
            )

            Spacer(Modifier.height(28.dp))

            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text(stringResource(R.string.label_name)) },
                supportingText = { Text(stringResource(R.string.label_name_hint)) },
                singleLine = true,
                enabled = !busy,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(Modifier.height(16.dp))

            OutlinedTextField(
                value = pin,
                onValueChange = { pin = it },
                label = { Text(stringResource(R.string.label_pin)) },
                supportingText = { Text(stringResource(R.string.label_pin_hint)) },
                singleLine = true,
                enabled = !busy,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.NumberPassword,
                    imeAction = ImeAction.Done,
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth(),
            )

            error?.let { message ->
                Spacer(Modifier.height(18.dp))
                Row(verticalAlignment = Alignment.Top) {
                    Icon(
                        painter = painterResource(R.drawable.ic_error),
                        contentDescription = null,
                        tint = Critical,
                        modifier = Modifier.size(20.dp),
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = message,
                        style = MaterialTheme.typography.bodyMedium,
                        color = Critical,
                    )
                }
            }

            Spacer(Modifier.height(32.dp))

            Button(
                onClick = { submit() },
                enabled = !busy,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(
                        color = Color.White,
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(20.dp),
                    )
                    Spacer(Modifier.width(12.dp))
                    Text(stringResource(R.string.signing_in))
                } else {
                    Text(
                        text = stringResource(R.string.action_sign_in),
                        style = MaterialTheme.typography.labelLarge,
                    )
                }
            }

            Spacer(Modifier.height(24.dp))
            Text(
                text = stringResource(R.string.sign_in_footer),
                style = MaterialTheme.typography.labelMedium,
                color = TextSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

/**
 * Sign in, then quietly do the three technical things the user should never
 * have to know about: store the key the server issued, remember the name, and
 * register this phone's push token.
 */
private fun CoroutineScope.launchSignIn(
    context: Context,
    name: String,
    pin: String,
    unreachable: String,
    wrongPin: String,
    notConfigured: String,
    tooManyFallback: String,
    onFailure: (String) -> Unit,
    onSuccess: (Int?) -> Unit,
) {
    launch {
        val result = withContext(Dispatchers.IO) { ApiClient.signIn(name, pin) }

        when (result) {
            is ApiClient.SignInResult.Unreachable -> onFailure(unreachable)
            is ApiClient.SignInResult.WrongPin -> onFailure(wrongPin)
            is ApiClient.SignInResult.NotConfigured -> onFailure(notConfigured)
            is ApiClient.SignInResult.TooManyAttempts ->
                onFailure(result.message.ifBlank { tooManyFallback })

            is ApiClient.SignInResult.Success -> {
                context.registrationKey = result.key
                context.displayName = result.name
                context.isSignedIn = true

                val registered = registerThisDevice(context)

                // Three separate ways to end up signed in but unwakeable, and
                // all are worth saying out loud rather than discovering at 3am.
                onSuccess(
                    when {
                        result.key.isBlank() -> R.string.warn_no_key
                        !result.pushEnabled -> R.string.warn_push_disabled
                        !registered -> R.string.error_push_token
                        else -> null
                    }
                )
            }
        }
    }
}
