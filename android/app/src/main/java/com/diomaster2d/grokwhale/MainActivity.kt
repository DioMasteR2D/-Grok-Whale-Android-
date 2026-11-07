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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private const val API_BASE = "https://diomaster2d-grok-whale-api.onrender.com"
private val Bg = Color(0xFF0B0912)
private val Panel = Color(0xFF171321)
private val Purple = Color(0xFF7655F5)
private val Green = Color(0xFF20D99A)
private val Muted = Color(0xFF8D879D)
private val Red = Color(0xFFFF667A)

data class SignalRow(val mint:String,val bias:String,val score:Int,val action:String,val buyers:Int,val sellers:Int,val confidence:String)
data class AppData(
    val online:Boolean=false,val status:String="Connecting…",val soul:String="—",val atlas:String="—",
    val discovery:String="—",val flow:String="—",val wallets:String="—",
    val signals:List<SignalRow> = emptyList(),val error:String=""
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { GrokBotApp() }
    }
}

@Composable
fun GrokBotApp() {
    var screen by remember { mutableStateOf("splash") }
    LaunchedEffect(Unit) { delay(1800); screen = "connect" }
    MaterialTheme(colorScheme = darkColorScheme(background=Bg,surface=Panel,primary=Purple,onBackground=Color.White,onSurface=Color.White)) {
        Surface(Modifier.fillMaxSize(),color=Bg) {
            when(screen) {
                "splash" -> SplashScreen()
                "connect" -> ConnectScreen { screen="dashboard" }
                else -> DashboardScreen()
            }
        }
    }
}

@Composable
private fun SplashScreen() {
    Column(Modifier.fillMaxSize().background(Bg),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center) {
        Text("◉",color=Color.White,fontSize=58.sp,fontWeight=FontWeight.Bold)
        Text("Grok Bot",fontSize=32.sp,fontWeight=FontWeight.Bold,color=Color.White)
        Text("terminal  •  whale mode",color=Muted,fontSize=12.sp)
        Spacer(Modifier.height(34.dp))
        LinearProgressIndicator(progress={0.99f},color=Purple,trackColor=Panel,modifier=Modifier.width(190.dp))
        Text("INITIALIZING WHALE INTELLIGENCE 99%",color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=10.dp))
    }
}

@Composable
private fun ConnectScreen(onContinue:()->Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp),verticalArrangement=Arrangement.Center) {
        Text("Grok Bot",color=Color.White,fontSize=25.sp,fontWeight=FontWeight.Bold)
        Text("whale mode",color=Purple,fontSize=12.sp)
        Spacer(Modifier.height(28.dp))
        Card(colors=CardDefaults.cardColors(containerColor=Panel),shape=RoundedCornerShape(24.dp)) {
            Column(Modifier.padding(22.dp),verticalArrangement=Arrangement.spacedBy(14.dp)) {
                Text("Whale intelligence",color=Color.White,fontSize=21.sp,fontWeight=FontWeight.Bold)
                Text("Open the live research dashboard. Phantom integration will follow after data and paper trading are verified.",color=Muted)
                Text("✓ Live backend status\n✓ Helius wallet activity signals\n✓ Paper mode only — no real orders",color=Green,fontSize=13.sp)
                Button(onClick=onContinue,modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=Purple)) { Text("Open dashboard") }
                Text("Phantom is not connected in this build. Never enter a seed phrase or private key.",color=Muted,fontSize=10.sp)
            }
        }
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
    val signalsJson=api("/api/v1/signals?limit=20")
    val arr=signalsJson.optJSONArray("items")
    val rows=buildList {
        if(arr!=null) for(i in 0 until arr.length()) {
            val x=arr.optJSONObject(i) ?: continue
            add(SignalRow(x.optString("mint"),x.optString("bias"),x.optInt("score"),x.optString("action"),x.optInt("wallets_buying"),x.optInt("wallets_selling"),x.optString("confidence")))
        }
    }
    AppData(
        online=true,status="API ONLINE",
        soul=src.optString("soulwinners_database","unknown"),
        atlas=src.optString("atlas_agent","unknown"),
        discovery=flow.optString("discovery","unknown"),
        flow=flow.optString("status","unknown"),
        wallets=flow.optInt("wallets_with_activity_response",0).toString()+" / "+flow.optInt("wallets_discovered",0),
        signals=rows
    )
} catch(e:Exception) {
    AppData(status="API CONNECTION ERROR",error=e.message ?: "Unknown error")
}

@Composable
private fun DashboardScreen() {
    var data by remember { mutableStateOf(AppData()) }
    var loading by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        while(true) {
            loading=true
            data=loadData()
            loading=false
            delay(60000)
        }
    }
    LazyColumn(Modifier.fillMaxSize().background(Bg).padding(horizontal=14.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        item {
            Row(Modifier.fillMaxWidth().padding(top=12.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
                Column {
                    Text("◉ Grok Bot",color=Color.White,fontWeight=FontWeight.Bold,fontSize=19.sp)
                    Text("whale mode  •  PAPER ONLY",color=Purple,fontSize=10.sp)
                }
                Text(if(data.online)"● API ONLINE" else "● OFFLINE",color=if(data.online)Green else Red,fontSize=9.sp)
            }
        }
        item {
            Text(if(loading)"SYNCING…" else data.status,color=if(data.online)Green else Red,fontSize=11.sp)
            if(data.error.isNotBlank()) Text(data.error,color=Red,fontSize=10.sp)
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(16.dp)).padding(16.dp)) {
                Text("PAPER PORTFOLIO",color=Muted,fontSize=10.sp)
                Text("$0.00",color=Color.White,fontSize=36.sp,fontWeight=FontWeight.Bold)
                Text("Paper engine not activated yet • live trading disabled",color=Green,fontSize=10.sp)
            }
        }
        item { SectionTitle("source status","live response from backend") }
        item { StatusRow("SoulWinners DB",data.soul) }
        item { StatusRow("Atlas Agent",data.atlas) }
        item { StatusRow("Wallet discovery",data.discovery) }
        item { StatusRow("Helius flow",data.flow) }
        item { StatusRow("Wallets responded",data.wallets) }
        item { SectionTitle("research signals","Helius transfer heuristic • not AI advice") }
        if(data.signals.isEmpty()) item { Text("No signals returned by API.",color=Muted,fontSize=11.sp,modifier=Modifier.padding(10.dp)) }
        else items(data.signals) { s ->
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(10.dp)).padding(12.dp)) {
                Text(s.mint,color=Color.White,fontSize=10.sp,fontWeight=FontWeight.Bold)
                Spacer(Modifier.height(5.dp))
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text(s.bias.uppercase()+" • "+s.action.uppercase(),color=Purple,fontSize=10.sp)
                    Text("SCORE "+s.score+"/100",color=Green,fontSize=10.sp,fontWeight=FontWeight.Bold)
                }
                Text("Buyers "+s.buyers+" • Sellers "+s.sellers+" • Confidence "+s.confidence,color=Muted,fontSize=9.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(16.dp)).padding(14.dp)) {
                Text("Atlas flow log",color=Color.White,fontSize=15.sp,fontWeight=FontWeight.Bold)
                Text("Atlas Agent not deployed yet. This panel reports the live backend source state.",color=Muted,fontSize=10.sp)
            }
        }
        item { Text("No wallet connection, signing, or live orders in this build.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(bottom=24.dp)) }
    }
}

@Composable
private fun StatusRow(label:String,value:String) {
    Row(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(8.dp)).padding(11.dp),horizontalArrangement=Arrangement.SpaceBetween) {
        Text(label,color=Muted,fontSize=10.sp); Text(value,color=Color.White,fontSize=10.sp)
    }
}

@Composable
private fun SectionTitle(title:String,subtitle:String) {
    Column(Modifier.padding(top=6.dp)) {
        Text(title,color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
        Text(subtitle,color=Muted,fontSize=9.sp)
    }
}
