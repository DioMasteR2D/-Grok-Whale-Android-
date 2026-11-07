package com.diomaster2d.grokwhale

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { GrokWhaleHome() }
    }
}

@Composable
fun GrokWhaleHome() {
    MaterialTheme {
        Scaffold { padding ->
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                item {
                    Text("DioMasteR2D", style = MaterialTheme.typography.headlineMedium)
                    Text("GROK WHALE MODE  •  Android alpha", style = MaterialTheme.typography.titleSmall)
                }
                item { StatusCard("SYSTEM", "Integration scaffold — data adapters pending") }
                item { StatusCard("WHALE INTELLIGENCE", "SolScope + SoulWinners wallet metrics") }
                item { StatusCard("ATLAS FLOW", "Origin → followers → propagation / crowding") }
                item { StatusCard("PORTFOLIO", "Paper mode only • no live trades") }
                item {
                    Text(
                        "Safety: no seed phrase or private key is requested. Live trading is not implemented.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusCard(title: String, detail: String) {
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(detail, style = MaterialTheme.typography.bodyMedium)
        }
    }
}
