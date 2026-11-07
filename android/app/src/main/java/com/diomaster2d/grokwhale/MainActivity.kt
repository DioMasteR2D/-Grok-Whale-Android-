package com.diomaster2d.grokwhale

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay

private val Bg = Color(0xFF0B0912)
private val Panel = Color(0xFF171321)
private val Purple = Color(0xFF7655F5)
private val Green = Color(0xFF20D99A)
private val Muted = Color(0xFF8D879D)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { GrokBotApp() }
    }
}

@Composable
fun GrokBotApp() {
    var screen by remember { mutableStateOf("splash") }
    LaunchedEffect(Unit) { delay(2200); screen = "connect" }
    MaterialTheme(colorScheme = darkColorScheme(background = Bg, surface = Panel, primary = Purple, onBackground = Color.White, onSurface = Color.White)) {
        Surface(Modifier.fillMaxSize(), color = Bg) {
            when (screen) {
                "splash" -> SplashScreen()
                "connect" -> ConnectScreen(onConnected = { screen = "dashboard" })
                else -> DashboardScreen()
            }
        }
    }
}

@Composable
private fun SplashScreen() {
    Column(Modifier.fillMaxSize().background(Bg), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text("◉", color = Color.White, fontSize = 58.sp, fontWeight = FontWeight.Bold)
        Text("Grok Bot", fontSize = 32.sp, fontWeight = FontWeight.Bold, color = Color.White)
        Text("terminal  •  whale mode", color = Muted, fontSize = 12.sp)
        Spacer(Modifier.height(34.dp))
        LinearProgressIndicator(progress = { 0.99f }, color = Purple, trackColor = Panel, modifier = Modifier.width(190.dp))
        Text("INITIALIZING WHALE INTELLIGENCE 99%", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(top=10.dp))
    }
}

@Composable
private fun ConnectScreen(onConnected: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Grok Bot", color = Color.White, fontSize = 25.sp, fontWeight = FontWeight.Bold)
        Text("whale mode", color = Purple, fontSize = 12.sp)
        Spacer(Modifier.height(28.dp))
        Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(24.dp)) {
            Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("Connect wallet", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
                Text("Connect Phantom to view wallet balance and activity.", color = Muted)
                Text("◎  Phantom  •  Solana", color = Color.White)
                Text("✓ View balance and activity\n✓ Approve every transaction\n✓ Grok Bot never holds your funds", color = Green, fontSize = 13.sp)
                Button(onClick = onConnected, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = Purple)) {
                    Text("Continue to demo dashboard")
                }
                Text("Demo navigation only — real Phantom connection is not wired yet.", color = Muted, fontSize = 10.sp)
            }
        }
    }
}

@Composable
private fun DashboardScreen() {
    val wallets = listOf("Core Alpha","Sniper","Early buyer","Momentum","Holder","Scout")
    val emojis = listOf("🟠","🟣","🔵","🟢","🟡","⚪")
    LazyColumn(Modifier.fillMaxSize().background(Bg).padding(horizontal = 14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Row(Modifier.fillMaxWidth().padding(top=12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("◉ Grok Bot", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 19.sp)
                    Text("whale mode  •  PAPER", color = Purple, fontSize = 10.sp)
                }
                Text("● DATA PENDING", color = Green, fontSize = 9.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(16.dp)).padding(16.dp)) {
                Text("PAPER PORTFOLIO", color = Muted, fontSize = 10.sp)
                Text("$0.00", color = Color.White, fontSize = 36.sp, fontWeight = FontWeight.Bold)
                Text("+$0.00  •  0.0%  •  0 of 10 whales traded", color = Green, fontSize = 11.sp)
                Spacer(Modifier.height(12.dp))
                ProfitChart()
                Text("portfolio value  →  time", color = Muted, fontSize = 9.sp)
            }
        }
        item { SectionTitle("whale wallets", "SolScope + SoulWinners") }
        items(wallets.size) { index ->
            Row(Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(10.dp)).padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(emojis[index], fontSize = 14.sp)
                    Spacer(Modifier.width(8.dp))
                    Column {
                        Text("Wallet " + (index+1) + "  •  " + wallets[index], color = Color.White, fontSize = 11.sp)
                        Text("waiting for verified wallet metrics", color = Muted, fontSize = 9.sp)
                    }
                }
                Text("—", color = Muted, fontSize = 12.sp)
            }
        }
        item { SectionTitle("atlas flow log", "origin • propagation • crowding") }
        items(listOf("SCAN","ORIGIN","FOLLOW","SECTOR","STATUS")) { label ->
            Row(Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(8.dp)).padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(label, color = Purple, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Text("Awaiting Atlas feed", color = Muted, fontSize = 10.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(16.dp)).padding(16.dp)) {
                Text("8h recap", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Text("Paper simulation summary", color = Muted, fontSize = 10.sp)
                Spacer(Modifier.height(10.dp))
                Text("$0.00", color = Green, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                Text("0 trades    •    0 memes    •    0 whales", color = Muted, fontSize = 11.sp)
            }
        }
        item { Text("All figures are placeholders until upstream data adapters are connected. No live trades.", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(bottom=24.dp)) }
    }
}

@Composable
private fun SectionTitle(title: String, subtitle: String) {
    Column(Modifier.padding(top=6.dp)) {
        Text(title, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Muted, fontSize = 9.sp)
    }
}

@Composable
private fun ProfitChart() {
    Canvas(Modifier.fillMaxWidth().height(110.dp)) {
        val path = Path().apply {
            moveTo(0f, size.height * .92f)
            lineTo(size.width * .18f, size.height * .88f)
            lineTo(size.width * .36f, size.height * .90f)
            lineTo(size.width * .53f, size.height * .70f)
            lineTo(size.width * .70f, size.height * .53f)
            lineTo(size.width * .86f, size.height * .28f)
            lineTo(size.width, size.height * .10f)
        }
        drawPath(path, Green, style = androidx.compose.ui.graphics.drawscope.Stroke(width=3.dp.toPx()))
    }
}
