package com.diomaster2d.grokwhale

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalTime
import java.time.format.DateTimeFormatter

private const val API_BASE = "https://diomaster2d-grok-whale-api.onrender.com"
private val Bg = Color(0xFF09080E)
private val Panel = Color(0xFF171423)
private val Panel2 = Color(0xFF211C32)
private val Purple = Color(0xFF7962F4)
private val Green = Color(0xFF22D69A)
private val Muted = Color(0xFF8B8599)
private val Amber = Color(0xFFE9A66A)
private val Red = Color(0xFFFF667A)

data class SignalRow(val mint:String,val bias:String,val score:Int,val action:String,val buyers:Int,val sellers:Int,val confidence:String)
data class WalletRow(val address:String,val archetype:String,val roi:Double,val winRate:Double,val trades:Int,val score:Double)
data class AppData(val online:Boolean=false,val status:String="Connecting…",val soul:String="—",val atlas:String="—",val discovery:String="—",val flow:String="—",val wallets:String="—",val signals:List<SignalRow> = emptyList(),val topWhales:List<WalletRow> = emptyList(),val error:String="")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { GrokBotApp() }
    }
}

@Composable
fun GrokBotApp() {
    var screen by remember { mutableStateOf("splash") }
    LaunchedEffect(Unit) { delay(1900); screen = "session" }
    MaterialTheme(colorScheme=darkColorScheme(background=Bg,surface=Panel,primary=Purple,onBackground=Color.White,onSurface=Color.White)) {
        Surface(Modifier.fillMaxSize(),color=Bg) {
            when(screen) {
                "splash" -> SplashScreen()
                "session" -> SessionScreen { screen="dashboard" }
                else -> DashboardScreen()
            }
        }
    }
}

@Composable
private fun SplashScreen() {
    Column(Modifier.fillMaxSize().background(Bg),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center) {
        Box(Modifier.size(72.dp).background(Panel2,RoundedCornerShape(22.dp)),contentAlignment=Alignment.Center) {
            Text("◖",color=Color.White,fontSize=48.sp,fontWeight=FontWeight.Black)
        }
        Spacer(Modifier.height(12.dp))
        Text("Grok Bot",fontSize=31.sp,fontWeight=FontWeight.Bold,color=Color.White)
        Text("terminal  •  whale mode",color=Muted,fontSize=12.sp)
        Spacer(Modifier.height(32.dp))
        LinearProgressIndicator(progress={0.99f},color=Purple,trackColor=Panel,modifier=Modifier.width(185.dp))
        Text("INITIALIZING 99%",color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=9.dp))
    }
}

@Composable
private fun SessionScreen(onStart:()->Unit) {
    Column(Modifier.fillMaxSize().background(Bg).padding(horizontal=18.dp, vertical=12.dp)) {
        Row(verticalAlignment=Alignment.CenterVertically) {
            Box(Modifier.size(38.dp).background(Panel2,RoundedCornerShape(12.dp)),contentAlignment=Alignment.Center) { Text("◖",color=Color.White,fontSize=25.sp) }
            Spacer(Modifier.width(10.dp))
            Text("Grok Bot",fontSize=22.sp,fontWeight=FontWeight.Bold,color=Color.White)
            Spacer(Modifier.width(12.dp))
            Text("new session",fontSize=12.sp,color=Muted,fontFamily=FontFamily.Monospace)
        }
        Spacer(Modifier.height(24.dp))
        Column(Modifier.fillMaxWidth().background(Panel2,RoundedCornerShape(22.dp)).padding(16.dp)) {
            Text("you  ·  prompt",color=Muted,fontSize=11.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(10.dp))
            Text("Grok, pull Solana whale wallets via SolScope (GMGN leaderboards) + SoulWinners. Phantom connected.",color=Color.White,fontSize=13.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Text("WALLET ANALYSIS → MEME TRADES. Session 13:30 → 21:30.",color=Amber,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(13.dp))
            Text("RANK every wallet by BES, keep the top 10:",color=Amber,fontSize=12.sp,fontFamily=FontFamily.Monospace)
            Text("– 30d win-rate 60%+, 15+ trades, ROI 50%+\n– archetypes: Core Alpha, Moonshot, Sniper\n– skip CEX, market makers, bridges, devs",color=Color.White,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(13.dp))
            Text("BUY a meme only if Atlas says ALL:",color=Amber,fontSize=12.sp,fontFamily=FontFamily.Monospace)
            Text("– origin wallet in top 10, PropagationScore 0.70+\n– 2+ whales follow within 5 min\n– crowding under 0.55, LP burned, mint revoked",color=Color.White,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(13.dp))
            Text("Size max 8%. Stop -6%. Exit when the whale exits.\nExecute via Phantom. Log wallet, score, reason.",color=Color.White,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
        }
        Spacer(Modifier.height(18.dp))
        Row(verticalAlignment=Alignment.CenterVertically) {
            Box(Modifier.size(32.dp).background(Panel2,RoundedCornerShape(10.dp)),contentAlignment=Alignment.Center){Text("◖",color=Color.White,fontSize=20.sp)}
            Spacer(Modifier.width(8.dp))
            Column {
                Text("Grok Bot",color=Color.White,fontWeight=FontWeight.Bold,fontSize=13.sp)
                Text("13:30",color=Muted,fontSize=10.sp)
            }
        }
        Spacer(Modifier.height(16.dp))
        Text("SolScope · live discovery is checked after dashboard opens",color=Muted,fontSize=10.sp,fontFamily=FontFamily.Monospace)
        Spacer(Modifier.weight(1f))
        Button(onClick=onStart,modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=Purple),shape=RoundedCornerShape(16.dp)) { Text("OPEN WHALE DASHBOARD") }
        Text("Wallet authorization is a separate Phantom approval step.",color=Muted,fontSize=9.sp,modifier=Modifier.align(Alignment.CenterHorizontally).padding(top=8.dp))
    }
}

private suspend fun api(path:String):JSONObject = withContext(Dispatchers.IO) {
    val c=URL(API_BASE+path).openConnection() as HttpURLConnection
    try {
        c.requestMethod="GET"; c.connectTimeout=12000; c.readTimeout=25000
        c.setRequestProperty("Accept","application/json")
        val code=c.responseCode
        val stream=if(code in 200..299)c.inputStream else c.errorStream
        val body=stream.bufferedReader().use{it.readText()}
        if(code !in 200..299) error("API HTTP "+code)
        JSONObject(body)
    } finally { c.disconnect() }
}

private suspend fun loadData():AppData = try {
    val status=api("/api/v1/status")
    val src=status.optJSONObject("sources") ?: JSONObject()
    val flow=api("/api/v1/atlas/flows?limit=10")
    val sig=api("/api/v1/signals?limit=20")
    val top=api("/api/v1/whales/top")
    val arr=sig.optJSONArray("items")
    val whaleArray=top.optJSONArray("items")
    val whaleRows=buildList {
        if(whaleArray!=null) for(i in 0 until whaleArray.length()) {
            val w=whaleArray.optJSONObject(i) ?: continue
            add(WalletRow(w.optString("wallet_address"),w.optString("cluster_name",w.optString("cluster_label","—")),w.optDouble("roi_pct",0.0),w.optDouble("profit_token_ratio",0.0),w.optInt("total_trades"),w.optDouble("priority_score",0.0)))
        }
    }
    val rows=buildList {
        if(arr!=null) for(i in 0 until arr.length()) {
            val x=arr.optJSONObject(i) ?: continue
            add(SignalRow(x.optString("mint"),x.optString("bias"),x.optInt("score"),x.optString("action"),x.optInt("wallets_buying"),x.optInt("wallets_selling"),x.optString("confidence")))
        }
    }
    AppData(online=true,status="LIVE DATA",soul=top.optString("status",src.optString("soulwinners_database","unknown")),atlas=src.optString("atlas_agent","not deployed"),discovery=flow.optString("discovery","unknown"),flow=flow.optString("status","unknown"),wallets=flow.optInt("wallets_with_activity_response",0).toString()+" / "+flow.optInt("wallets_discovered",0),signals=rows,topWhales=whaleRows)
} catch(e:Exception) { AppData(status="API OFFLINE",error=e.message ?: "Unknown error") }

@Composable
private fun DashboardScreen() {
    var data by remember { mutableStateOf(AppData()) }
    var loading by remember { mutableStateOf(false) }
    var walletLabel by remember { mutableStateOf("Phantom not connected") }
    var showConnectInfo by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        while(true) { loading=true; data=loadData(); loading=false; delay(60000) }
    }
    LazyColumn(Modifier.fillMaxSize().background(Bg).padding(horizontal=13.dp),verticalArrangement=Arrangement.spacedBy(9.dp)) {
        item {
            Row(Modifier.fillMaxWidth().padding(top=10.dp),verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(35.dp).background(Panel2,RoundedCornerShape(12.dp)),contentAlignment=Alignment.Center){Text("◖",color=Color.White,fontSize=24.sp)}
                Spacer(Modifier.width(8.dp))
                Column(Modifier.weight(1f)) {
                    Text("Grok Bot",color=Color.White,fontSize=18.sp,fontWeight=FontWeight.Bold)
                    Text("whale mode",color=Muted,fontSize=10.sp)
                }
                Text(if(data.online)"● Live" else "● Offline",color=if(data.online)Green else Red,fontSize=11.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(18.dp)).padding(15.dp)) {
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text("trading session 13:30 → 21:30",color=Muted,fontSize=9.sp)
                    Text(if(data.online)"● synced" else "● offline",color=if(data.online)Green else Red,fontSize=9.sp)
                }
                Text("—",color=Color.White,fontSize=37.sp,fontWeight=FontWeight.Bold)
                Text("Portfolio balance unavailable · paper/live accounting not connected",color=Muted,fontSize=9.sp)
                Spacer(Modifier.height(8.dp))
                Text("No fabricated PnL · live orders disabled until wallet and execution checks are complete",color=Amber,fontSize=9.sp)
            }
        }
        item {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
                Text("whale wallets",color=Color.White,fontSize=15.sp,fontWeight=FontWeight.Bold)
                Text("SolScope · SoulWinners",color=Muted,fontSize=9.sp)
            }
        }
        item { StatusRow("SolScope discovery",data.discovery) }
        item { StatusRow("SoulWinners DB",data.soul) }
        item { StatusRow("Atlas Agent",data.atlas) }
        item { StatusRow("Helius flow",data.flow) }
        item { StatusRow("Wallet responses",data.wallets) }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Text("SOULWINNERS · TOP 10",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Text("Original priority_score ranking · qualification gates",color=Muted,fontSize=9.sp)
                Spacer(Modifier.height(7.dp))
                if(data.topWhales.isEmpty()) {
                    Text("No qualified SoulWinners wallets returned. The original pipeline must populate its database.",color=Amber,fontSize=10.sp)
                } else {
                    data.topWhales.forEachIndexed { index,w ->
                        Text("${index+1}. ${w.address.take(5)}…${w.address.takeLast(5)}  ${w.archetype}",color=Color.White,fontSize=10.sp)
                        Text("ROI ${"%.1f".format(w.roi)}% · Win ${(w.winRate*100).toInt()}% · ${w.trades} trades · score ${"%.3f".format(w.score)}",color=Muted,fontSize=9.sp)
                        Spacer(Modifier.height(5.dp))
                    }
                }
            }
        }
        if(data.error.isNotBlank()) item { Text(data.error,color=Red,fontSize=10.sp) }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text("atlas flow log",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                    Text(if(loading)"syncing" else "stream",color=Green,fontSize=9.sp)
                }
                Spacer(Modifier.height(8.dp))
                Text(if(data.signals.isEmpty()) "Waiting for verified Atlas alerts…" else data.signals.take(8).joinToString("\n") { "• ${it.action.uppercase()}  ${it.mint.take(8)}…  score ${it.score}" },color=Muted,fontSize=10.sp,lineHeight=17.sp,fontFamily=FontFamily.Monospace)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Text("wallet connection",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Text(walletLabel,color=Muted,fontSize=10.sp)
                Button(onClick={showConnectInfo=true},modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=Purple)) { Text("Connect Phantom") }
                Text("Phantom connection will be enabled after the dashboard and session data are verified. Never enter a seed phrase or private key here.",color=Muted,fontSize=9.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Text("8H SESSION RECAP",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                Text("Capital deployed: —     PnL: —",color=Muted,fontSize=10.sp)
                Text("Trades: —     Memes: —     Whales: —",color=Muted,fontSize=10.sp)
                Text("Recap will populate from verified session and paper-trade records.",color=Amber,fontSize=9.sp)
            }
        }
        item { Text("Phantom authorization is the next integration step. No wallet has been connected yet.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(bottom=20.dp)) }
    }
    if(showConnectInfo) AlertDialog(
        onDismissRequest={showConnectInfo=false},
        title={Text("Phantom connection")},
        text={Text("Native Mobile Wallet Adapter dependency is included. The authorization flow still needs its Activity-result integration and device verification before this can report a connected wallet.")},
        confirmButton={ TextButton(onClick={ showConnectInfo = false }) { Text("OK") } }
    )
}

@Composable
private fun StatusRow(label:String,value:String) {
    Row(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(9.dp)).padding(10.dp),horizontalArrangement=Arrangement.SpaceBetween) {
        Text(label,color=Muted,fontSize=10.sp); Text(value,color=Color.White,fontSize=10.sp)
    }
}
