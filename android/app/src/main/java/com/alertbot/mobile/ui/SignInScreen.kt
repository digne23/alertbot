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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.navigationBarsPadding
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
import com.alertbot.mobile.data.DEFAULT_SERVER_URL
import com.alertbot.mobile.data.baseUrl
import com.alertbot.mobile.data.isSignedIn
import com.alertbot.mobile.data.password
import com.alertbot.mobile.data.registerThisDevice
import com.alertbot.mobile.data.registrationKey
import com.alertbot.mobile.data.username
import com.alertbot.mobile.ui.components.BrandMark
import com.alertbot.mobile.ui.theme.BrandBlue
import com.alertbot.mobile.ui.theme.Critical
import com.alertbot.mobile.ui.theme.TextSecondary
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The whole of first-run setup. Three fields, one button.
 *
 * The server's device registration key is never shown: it is fetched from
 * `/api/health` with the credentials the user just proved, so nobody has to
 * copy a token between a dashboard and a phone.
 */
@Composable
fun SignInScreen(onSignedIn: (warningRes: Int?) -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var server by remember {
        mutableStateOf(context.baseUrl.ifBlank { DEFAULT_SERVER_URL })
    }
    var user by remember { mutableStateOf(context.username) }
    var secret by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    val unreachable = stringResource(R.string.error_unreachable)
    val badCredentials = stringResource(R.string.error_bad_credentials)
    val noServer = stringResource(R.string.error_no_server)

    fun submit() {
        val url = ApiClient.normaliseUrl(server)
        if (url.isEmpty()) {
            error = noServer
            return
        }

        busy = true
        error = null
        scope.launchSignIn(
            context = context,
            creds = ApiClient.Creds(url, user.trim(), secret),
            onFailure = { message ->
                busy = false
                error = message
            },
            onSuccess = { warningRes ->
                busy = false
                onSignedIn(warningRes)
            },
            unreachable = unreachable,
            badCredentials = badCredentials,
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
                value = server,
                onValueChange = { server = it },
                label = { Text(stringResource(R.string.label_server)) },
                singleLine = true,
                enabled = !busy,
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Uri,
                    imeAction = ImeAction.Next,
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(Modifier.height(16.dp))

            OutlinedTextField(
                value = user,
                onValueChange = { user = it },
                label = { Text(stringResource(R.string.label_username)) },
                singleLine = true,
                enabled = !busy,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(Modifier.height(16.dp))

            OutlinedTextField(
                value = secret,
                onValueChange = { secret = it },
                label = { Text(stringResource(R.string.label_password)) },
                singleLine = true,
                enabled = !busy,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Password,
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
 * have to know about: store the credentials, fetch the registration key, and
 * register this phone's push token.
 */
private fun CoroutineScope.launchSignIn(
    context: Context,
    creds: ApiClient.Creds,
    unreachable: String,
    badCredentials: String,
    onFailure: (String) -> Unit,
    onSuccess: (Int?) -> Unit,
) {
    launch {
        val result = withContext(Dispatchers.IO) { ApiClient.signIn(creds) }

        when (result) {
            is ApiClient.SignInResult.Unreachable -> onFailure(unreachable)
            is ApiClient.SignInResult.BadCredentials -> onFailure(badCredentials)
            is ApiClient.SignInResult.Success -> {
                context.baseUrl = creds.baseUrl
                context.username = creds.username
                context.password = creds.password
                context.isSignedIn = true

                withContext(Dispatchers.IO) {
                    context.registrationKey = ApiClient.fetchRegistrationKey(
                        creds.copy(baseUrl = context.baseUrl)
                    )
                }
                val registered = registerThisDevice(context)

                // Two separate ways to end up signed in but unwakeable, and
                // both are worth saying out loud rather than discovering at 3am.
                onSuccess(
                    when {
                        !result.pushEnabled -> R.string.warn_push_disabled
                        !registered -> R.string.error_push_token
                        else -> null
                    }
                )
            }
        }
    }
}
