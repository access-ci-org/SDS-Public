import { showAlert } from "./alerts.js"

// ── Download settings ─────────────────────────────────────────────────────────

$("#download-software-csv").click(function (){
    showAlert("Preparing download...", 'info')
    window.location = "/download_software_csv"
})

$("#download-software-json").click(function () {
    showAlert("Preparing download...", 'info')
    window.location = "/download_software_json"
})

$("#download-analytics-json").click(function () {
    showAlert("Preparing download...", 'info')
    window.location = "/download_analytics_json"
})
