package com.diomaster2d.grokwhale

import android.os.Bundle
import android.net.Uri
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
import com.solana.mobilewalletadapter.clientlib.ActivityResultSender
import com.solana.mobilewalletadapter.clientlib.ConnectionIdentity
import com.solana.mobilewalletadapter.clientlib.MobileWalletAdapter
import com.solana.mobilewalletadapter.clientlib.Solana
import com.solana.mobilewalletadapter.clientlib.TransactionResult
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalTime
import java.time.format.DateTimeFormatter

private const val API_BASE = BuildConfig.API_BASE_URL
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
data class AppData(val online:Boolean=false,val status:String="Connecting…",val soul:String="—",val atlas:String="—",val discovery:String="—",val flow:String="—",val wallets:String="—",val signals:List<SignalRow> = emptyList(),val topWhales:List<WalletRow> = emptyList(),val readiness:String="Checking execution safety…",val blockers:List<String> = emptyList(),val paperSummary:String="Paper portfolio unavailable",val sessionSummary:String="Session recap unavailable",val error:String="")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val walletSender = ActivityResultSender(this)
        val walletAdapter = MobileWalletAdapter(
            ConnectionIdentity(
                Uri.parse("https://diomaster2d.app"),
                Uri.parse("favicon.ico"),
                "DioMasteR2D Grok Bot"
            )
        ).apply { blockchain = Solana.Mainnet }
        setContent { GrokBotApp(walletSender, walletAdapter) }
    }
}

@Composable
fun GrokBotApp(walletSender: ActivityResultSender, walletAdapter: MobileWalletAdapter) {
    var screen by remember { mutableStateOf("splash") }
    LaunchedEffect(Unit) { delay(1900); screen = "session" }
    MaterialTheme(colorScheme=darkColorScheme(background=Bg,surface=Panel,primary=Purple,onBackground=Color.White,onSurface=Color.White)) {
        Surface(Modifier.fillMaxSize(),color=Bg) {
            when(screen) {
                "splash" -> SplashScreen()
                "session" -> SessionScreen { screen="dashboard" }
                else -> DashboardScreen(walletSender, walletAdapter)
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
            Text("Grok, pull Solana whale wallets via SolScope (GMGN leaderboards) + SoulWinners. Connect Phantom securely when requested.",color=Color.White,fontSize=13.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Text("WALLET ANALYSIS → MEME TRADES. Session 13:30 → 21:30.",color=Amber,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(13.dp))
            Text("RANK every wallet by BES, keep the top 10:",color=Amber,fontSize=12.sp,fontFamily=FontFamily.Monospace)
            Text("– 30d win-rate 60%+, 15+ trades, ROI 50%+\n– archetypes: Core Alpha, Moonshot, Sniper\n– skip CEX, market makers, bridges, devs",color=Color.White,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(13.dp))
            Text("BUY a meme only if Atlas says ALL:",color=Amber,fontSize=12.sp,fontFamily=FontFamily.Monospace)
            Text("– origin wallet in top 10, PropagationScore 0.70+\n– 2+ whales follow within 5 min\n– crowding under 0.55, LP burned, mint revoked",color=Color.White,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
            Spacer(Modifier.height(13.dp))
            Text("Size max 8%. Stop -6%. Exit when the whale exits.\nPaper-only. Phantom connection is read-only; no signing or sending. Log wallet, score, reason.",color=Color.White,fontSize=12.sp,lineHeight=19.sp,fontFamily=FontFamily.Monospace)
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

private suspend fun apiPost(path:String):JSONObject {
    return withContext(Dispatchers.IO) {
        val connection=URL(API_BASE+path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod="POST"
            connection.doOutput=true
            connection.connectTimeout=15000
            connection.readTimeout=45000
            connection.setRequestProperty("Accept","application/json")
            connection.setRequestProperty("Content-Type","application/json")
            connection.outputStream.use { it.write("{}".toByteArray()) }
            val code=connection.responseCode
            val stream=if(code in 200..299) connection.inputStream else connection.errorStream
            val body=stream.bufferedReader().use{it.readText()}
            if(code !in 200..299) error("API HTTP "+code+": "+body.take(180))
            JSONObject(body)
        } finally { connection.disconnect() }
    }
}

private suspend fun api(path:String):JSONObject {
    var lastError:Exception? = null
    for (attempt in 0..4) {
        try {
            return withContext(Dispatchers.IO) {
                val connection=URL(API_BASE+path).openConnection() as HttpURLConnection
                try {
                    connection.requestMethod="GET"
                    connection.connectTimeout=15000
                    connection.readTimeout=25000
                    connection.setRequestProperty("Accept","application/json")
                    val code=connection.responseCode
                    val stream=if(code in 200..299) connection.inputStream else connection.errorStream
                    val body=stream.bufferedReader().use{it.readText()}
                    if(code !in 200..299) error("API HTTP "+code)
                    JSONObject(body)
                } finally { connection.disconnect() }
            }
        } catch (e:Exception) {
            lastError=e
            if (attempt < 4) delay(1500L * (1L shl attempt))
        }
    }
    throw IllegalStateException("API unavailable after 5 attempts: "+(lastError?.message ?: "network error"),lastError)
}

private suspend fun loadData():AppData {
    // Health is the only connectivity gate. A failed optional endpoint must not
    // mark the whole app offline when the API itself is reachable.
    val health = runCatching { api("/health") }.getOrElse {
        return AppData(status="API OFFLINE",error=it.message ?: "Health check failed")
    }
    val status = runCatching { api("/api/v1/status") }.getOrNull() ?: JSONObject()
    val src=status.optJSONObject("sources") ?: JSONObject()
    val flow=runCatching { api("/api/v1/atlas/flows?limit=10") }.getOrNull() ?: JSONObject()
    val agent=runCatching { apiPost("/api/v1/atlas/agent/scan?limit=10") }.getOrNull()
    val sig=runCatching { api("/api/v1/signals?limit=20") }.getOrNull() ?: JSONObject()
    val top=runCatching { api("/api/v1/whales/top") }.getOrNull() ?: JSONObject()
    val readiness=runCatching { api("/api/v1/execution/readiness") }.getOrNull() ?: JSONObject()
    // Paper endpoints are independent; preserve live API status if the database is unavailable.
    runCatching { api("/api/v1/paper/refresh") }
    val paper=runCatching { api("/api/v1/paper-portfolio") }.getOrNull() ?: JSONObject()
    val session=runCatching { api("/api/v1/paper/session-summary") }.getOrNull()
    val arr=sig.optJSONArray("items")
    val whaleArray=top.optJSONArray("items")
    val whaleRows=buildList {
        if(whaleArray!=null) for(i in 0 until whaleArray.length()) {
            val w=whaleArray.optJSONObject(i) ?: continue
            val winRate = if (w.has("win_rate") && !w.isNull("win_rate")) w.optDouble("win_rate") else Double.NaN
            add(WalletRow(w.optString("wallet_address"),w.optString("cluster_name",w.optString("cluster_label","—")),w.optDouble("roi_pct",0.0),winRate,w.optInt("total_trades"),w.optDouble("bes_score",0.0)))
        }
    }
    val rows=buildList {
        if(arr!=null) for(i in 0 until arr.length()) {
            val x=arr.optJSONObject(i) ?: continue
            add(SignalRow(x.optString("mint"),x.optString("bias"),x.optInt("score"),x.optString("action"),x.optInt("wallets_buying"),x.optInt("wallets_selling"),x.optString("confidence")))
        }
    }
    val agentStatus = when {
        agent == null -> "scan unavailable"
        agent.optString("status").isNotBlank() -> agent.optString("status")
        agent.optJSONArray("alerts") != null -> "scan complete · "+agent.optJSONArray("alerts")!!.length()+" alerts"
        else -> "scan returned"
    }
    val paperOk = paper.optString("status")=="ok"
    val paperText = if(paperOk) "Equity $"+paper.optDouble("equity",0.0)+" · Cash $"+paper.optDouble("cash",0.0)+" · Open "+(paper.optJSONArray("open_positions")?.length() ?: 0)+" · Realized PnL $"+paper.optDouble("realized_pnl",0.0) else "Paper portfolio unavailable · "+paper.optString("status","no response")
    val issues = buildList {
        if(status.length()==0) add("status endpoint unavailable")
        if(flow.length()==0) add("Atlas flow endpoint unavailable")
        if(sig.length()==0) add("signals endpoint unavailable")
        if(top.length()==0) add("SoulWinners endpoint unavailable")
        if(!paperOk) add("paper database unavailable")
    }
    AppData(online=true,status="API ONLINE · HEALTH CHECK OK",soul=top.optString("status",src.optString("soulwinners_database","unknown")),atlas=agentStatus,discovery=flow.optString("discovery","unknown"),flow=flow.optString("status","unknown"),wallets=flow.optInt("wallets_with_activity_response",0).toString()+" / "+flow.optInt("wallets_discovered",0),signals=rows,topWhales=whaleRows,readiness=if(readiness.optBoolean("ready_for_live_execution")) "Readiness reported ready · live still disabled" else "LIVE EXECUTION BLOCKED",blockers=buildList { val b=readiness.optJSONArray("blockers"); if(b!=null) for(i in 0 until b.length()) add(b.optString(i)) },paperSummary=paperText,sessionSummary=if(session != null && session.optString("status")=="ok") "Capital $"+"%.2f".format(session.optDouble("capital_deployed_usd"))+" · PnL $"+ "%.2f".format(session.optDouble("total_pnl_usd"))+" (realized $"+"%.2f".format(session.optDouble("realized_pnl_usd"))+")\nTrades "+session.optInt("trades")+" · Memes "+session.optInt("memes")+" · Whales "+session.optInt("whales")+"\nClosed "+session.optInt("closed_positions")+" · Open "+session.optInt("open_positions") else "Verified session records unavailable",error=issues.joinToString(" · "))
}
@Composable
private fun DashboardScreen(walletSender: ActivityResultSender, walletAdapter: MobileWalletAdapter) {
    var data by remember { mutableStateOf(AppData()) }
    var loading by remember { mutableStateOf(false) }
    var walletLabel by remember { mutableStateOf("Phantom not connected") }
    var walletBusy by remember { mutableStateOf(false) }
    var walletError by remember { mutableStateOf("") }
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
                Text(if(data.online)"● API Online" else "● Offline",color=if(data.online)Green else Red,fontSize=11.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(18.dp)).padding(15.dp)) {
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text("trading session 13:30 → 21:30",color=Muted,fontSize=9.sp)
                    Text(if(data.online)"● synced" else "● offline",color=if(data.online)Green else Red,fontSize=9.sp)
                }
                Text(if(data.online) "PAPER" else "—",color=Color.White,fontSize=37.sp,fontWeight=FontWeight.Bold)
                Text(data.paperSummary,color=Muted,fontSize=9.sp)
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
                Text("EXECUTION SAFETY",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Text(data.readiness,color=Amber,fontSize=11.sp,fontWeight=FontWeight.Bold)
                if(data.blockers.isNotEmpty()) Text(data.blockers.joinToString("\n") { "• "+it },color=Muted,fontSize=9.sp,lineHeight=15.sp)
                Text("LIVE ORDERS STAY DISABLED · Phantom approval required for every transaction",color=Red,fontSize=9.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Text("PAPER PORTFOLIO",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Text(data.paperSummary,color=Muted,fontSize=10.sp)
                Text("Simulation data only; no real SOL or tokens are moved.",color=Amber,fontSize=9.sp)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Text("SOULWINNERS · TOP 10",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Text("30-day filters · ranked by verified BES",color=Muted,fontSize=9.sp)
                Spacer(Modifier.height(7.dp))
                if(data.topWhales.isEmpty()) {
                    Text("No qualified SoulWinners wallets returned. The original pipeline must populate its database.",color=Amber,fontSize=10.sp)
                } else {
                    data.topWhales.forEachIndexed { index,w ->
                        Text("${index+1}. ${w.address.take(5)}…${w.address.takeLast(5)}  ${w.archetype}",color=Color.White,fontSize=10.sp)
                        val winText = if (w.winRate.isFinite()) "${"%.1f".format(w.winRate * 100)}%" else "N/A"
                        Text("ROI ${"%.1f".format(w.roi)}% · Win $winText · ${w.trades} trades · BES ${"%.4f".format(w.score)}",color=Muted,fontSize=9.sp)
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
                    Text(if(loading)"syncing" else "polling",color=Green,fontSize=9.sp)
                }
                Spacer(Modifier.height(8.dp))
                Text(if(data.signals.isEmpty()) "Waiting for verified Atlas alerts…" else data.signals.take(8).joinToString("\n") { "• ${it.action.uppercase()}  ${it.mint.take(8)}…  score ${it.score}" },color=Muted,fontSize=10.sp,lineHeight=17.sp,fontFamily=FontFamily.Monospace)
            }
        }
        item {
            Column(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(17.dp)).padding(13.dp)) {
                Text("wallet connection",color=Color.White,fontSize=14.sp,fontWeight=FontWeight.Bold)
                Text(walletLabel,color=Muted,fontSize=10.sp)
                Button(
                    onClick = { if (!walletBusy) { walletBusy = true; walletError = "" } },
                    modifier=Modifier.fillMaxWidth(),
                    colors=ButtonDefaults.buttonColors(containerColor=Purple)
                ) { Text(if (walletBusy) "Connecting…" else "Connect Phantom") }
                Text("Secure wallet authorization via Solana Mobile Wallet Adapter. No seed phrase or private key is requested.",color=Muted,fontSize=9.sp)
                if (walletError.isNotBlank()) Text(walletError,color=Red,fontSize=9.sp)
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
        item { Text("Wallet approval remains inside Phantom. No private keys are handled by this app.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(bottom=20.dp)) }
    }
    LaunchedEffect(walletBusy) {
        if (walletBusy) {
            try {
                when (val result = walletAdapter.connect(walletSender)) {
                    is TransactionResult.Success -> {
                        val account = result.authResult.accounts.firstOrNull()
                            ?: error("Wallet returned no authorized account")
                        val address = base58(account.publicKey)
                        walletLabel = "Connected: " + address.take(6) + "…" + address.takeLast(6)
                    }
                    is TransactionResult.NoWalletFound -> walletError = "No compatible wallet found. Open Phantom and try again."
                    is TransactionResult.Failure -> walletError = result.message
                }
            } catch (e: Exception) {
                walletError = e.message ?: "Wallet connection failed"
            } finally {
                walletBusy = false
            }
        }
    }
}

private fun base58(input: ByteArray): String {
    val alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    if (input.isEmpty()) return ""
    val digits = mutableListOf<Int>()
    for (byte in input) {
        var carry = byte.toInt() and 0xff
        for (i in digits.indices) {
            carry += digits[i] shl 8
            digits[i] = carry % 58
            carry /= 58
        }
        while (carry > 0) {
            digits.add(carry % 58)
            carry /= 58
        }
    }
    val zeros = input.takeWhile { it.toInt() == 0 }.count()
    return "1".repeat(zeros) + digits.asReversed().joinToString("") { alphabet[it].toString() }
}

@Composable
private fun StatusRow(label:String,value:String) {
    Row(Modifier.fillMaxWidth().background(Panel,RoundedCornerShape(9.dp)).padding(10.dp),horizontalArrangement=Arrangement.SpaceBetween) {
        Text(label,color=Muted,fontSize=10.sp); Text(value,color=Color.White,fontSize=10.sp)
    }
}
