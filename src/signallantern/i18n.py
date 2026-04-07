from __future__ import annotations

import locale
from dataclasses import dataclass

_TRANSLATIONS = {
    "sv": {
        "Signal Lantern": "Signal Lantern",
        "System health helper": "Systemhjälp för hälsa och nätverk",
        "Explains common network and system problems in plain language": "Förklarar vanliga nätverks- och systemproblem på begriplig svenska",
        "Overview": "Översikt",
        "System details": "Systemdetaljer",
        "About": "Om",
        "Check again now": "Kontrollera igen nu",
        "Run all health checks immediately": "Kör alla hälsokontroller direkt",
        "Keyboard shortcuts": "Tangentbordsgenvägar",
        "Ctrl+R checks again, Ctrl+Shift+C copies diagnostics": "Ctrl+R kör kontroller igen, Ctrl+Skift+C kopierar diagnostik",
        "Everything looks fine": "Allt ser bra ut",
        "Your system looks healthy.": "Ditt system verkar må bra.",
        "Needs attention": "Behöver uppmärksamhet",
        "Critical issue detected": "Kritiskt problem upptäckt",
        "What this means": "Det här betyder",
        "What you can try": "Det här kan du prova",
        "Technical details": "Tekniska detaljer",
        "Show technical details": "Visa tekniska detaljer",
        "Show technical details (press Enter or Space)": "Visa tekniska detaljer (tryck Enter eller blanksteg)",
        "Last checked": "Senast kontrollerad",
        "System health summary": "Systemhälsans sammanfattning",
        "Active issues": "Aktiva problem",
        "No active issues": "Inga aktiva problem",
        "Signal Lantern will let you know if it spots a network or system problem.": "Signal Lantern säger till om den hittar ett nätverks- eller systemproblem.",
        "Healthy": "Friskt",
        "Warning": "Varning",
        "Critical": "Kritiskt",
        "No network connection": "Ingen nätverksanslutning",
        "Weak Wi-Fi signal": "Svag Wi‑Fi-signal",
        "Router is not responding": "Routern svarar inte",
        "DNS lookups are slow": "DNS-uppslag är långsamma",
        "DNS is failing": "DNS fungerar inte",
        "High processor load": "Hög processorbelastning",
        "System is low on memory": "Systemet har lite minne kvar",
        "Disk space is running low": "Diskutrymmet börjar ta slut",
        "Your computer does not seem to be connected to Wi-Fi or wired Ethernet right now.": "Datorn verkar inte vara ansluten till Wi‑Fi eller kabelnätverk just nu.",
        "Your wireless connection is active, but the signal is weak and may cause slow speeds or dropouts.": "Den trådlösa anslutningen är aktiv, men signalen är svag och kan ge låg hastighet eller avbrott.",
        "Your computer is connected to the local network, but the default gateway is not replying.": "Datorn är ansluten till det lokala nätverket, men standard-gatewayen svarar inte.",
        "The DNS server is answering, but lookups are slower than normal.": "DNS-servern svarar, men uppslagen är långsammare än normalt.",
        "The DNS server does not appear to be answering reliably.": "DNS-servern verkar inte svara pålitligt.",
        "Your system has been under heavy CPU load for a while. Apps may feel slow or unresponsive.": "Systemet har haft hög CPU-belastning en stund. Appar kan kännas långsamma eller sega.",
        "Available memory is running low. Apps may freeze or swap heavily.": "Tillgängligt minne börjar ta slut. Appar kan frysa eller swappa mycket.",
        "Your main disk is almost full. Downloads, updates, and apps may start failing.": "Huvuddisken är nästan full. Hämtningar, uppdateringar och appar kan börja fallera.",
        "Check that Wi-Fi is turned on.": "Kontrollera att Wi‑Fi är aktiverat.",
        "Reconnect to your wireless network.": "Anslut till ditt trådlösa nätverk igen.",
        "Plug in the network cable if you use wired internet.": "Anslut nätverkskabeln om du använder kabelanslutning.",
        "Move closer to the router or access point.": "Flytta dig närmare routern eller accesspunkten.",
        "Reduce obstacles between your device and the router.": "Minska hinder mellan enheten och routern.",
        "Use Ethernet for a more stable connection if possible.": "Använd Ethernet för stabilare anslutning om det går.",
        "Restart the router if you can.": "Starta om routern om du kan.",
        "Reconnect to your network connection.": "Anslut till nätverket igen.",
        "Try another device on the same network to compare.": "Prova en annan enhet på samma nätverk för att jämföra.",
        "Wait a minute and try again in case the problem is temporary.": "Vänta en minut och försök igen om problemet är tillfälligt.",
        "Switch DNS server in network settings if you know a better one.": "Byt DNS-server i nätverksinställningarna om du vet en bättre.",
        "Restart the network connection or router.": "Starta om nätverksanslutningen eller routern.",
        "Try another network if websites still do not load.": "Prova ett annat nätverk om webbplatser fortfarande inte laddar.",
        "Close apps you do not need.": "Stäng appar du inte behöver.",
        "Check which process is using the CPU in System Monitor.": "Kontrollera vilken process som använder CPU i Systemövervakning.",
        "Restart the system if the load does not drop.": "Starta om systemet om belastningen inte går ned.",
        "Close large apps or browser tabs you do not need.": "Stäng stora appar eller webbläsarflikar du inte behöver.",
        "Restart heavy apps that may be leaking memory.": "Starta om tunga appar som kan läcka minne.",
        "Reboot if memory pressure stays high.": "Starta om datorn om minnespressen består.",
        "Delete large files you no longer need.": "Ta bort stora filer du inte längre behöver.",
        "Empty the trash.": "Töm papperskorgen.",
        "Move files to external or cloud storage.": "Flytta filer till extern lagring eller molnlagring.",
        "Open Network Settings": "Öppna nätverksinställningar",
        "Open System Monitor": "Öppna systemövervakning",
        "Open Disk Usage Analyzer": "Öppna diskanalys",
        "Copy diagnostics": "Kopiera diagnostik",
        "Copy full diagnostic report to clipboard": "Kopiera fullständig diagnostikrapport till urklipp",
        "Re-run checks": "Kör kontroller igen",
        "Issue details": "Problemdetaljer",
        "Current status": "Nuvarande status",
        "Seen": "Sedd",
        "Unknown": "Okänt",
        "Diagnostics copied to the clipboard.": "Diagnostik kopierad till urklipp.",
        "Beginner-friendly issue explanations with advanced details when you want them.": "Nybörjarvänliga förklaringar med tekniska detaljer när du vill ha dem.",
        "Quick health strip for advanced users.": "Snabb hälsoremsa för avancerade användare.",
        "No suitable desktop helper was found for this action.": "Ingen passande skrivbordshjälpare hittades för den här åtgärden.",
        "Open network settings and reconnect to get back online.": "Öppna nätverksinställningarna och anslut igen för att komma online.",
        "Move closer to the router or switch to a stronger connection.": "Flytta dig närmare routern eller byt till en starkare anslutning.",
        "Reconnect or troubleshoot the local network hardware.": "Anslut igen eller felsök den lokala nätverksutrustningen.",
        "Name lookups are slow, so websites may feel sluggish.": "Namnuppslag är långsamma, så webbplatser kan kännas sega.",
        "Websites may fail to load until name resolution works again.": "Webbplatser kan sluta ladda tills namnuppslag fungerar igen.",
        "Close a few heavy apps or inspect System Monitor.": "Stäng några tunga appar eller öppna Systemövervakning.",
        "Close a few large apps to keep the system responsive.": "Stäng några stora appar för att hålla systemet responsivt.",
        "Free some space so updates and downloads do not fail.": "Frigör utrymme så att uppdateringar och hämtningar inte misslyckas.",
        "Online": "Online",
        "Offline": "Offline",
        "Network": "Nätverk",
        "Wi-Fi": "Wi‑Fi",
        "Gateway": "Gateway",
        "DNS": "DNS",
        "CPU": "CPU",
        "Memory": "Minne",
        "Disk": "Disk",
        "Reachable": "Nåbar",
        "Unreachable": "Onåbar",
        "Failing": "Fallerar",
        "N/A": "Ej tillämpligt",
        "OK": "OK",
        "Weak": "Svag",
        "issue": "problem",
        "issues": "problem",
        "2 issues need attention.": "2 problem behöver uppmärksamhet.",
    }
}


@dataclass
class I18n:
    language: str

    def gettext(self, text: str) -> str:
        lang = self.language.split("_")[0].split("-")[0]
        return _TRANSLATIONS.get(lang, {}).get(text, text)



def detect_language() -> str:
    lang = locale.getlocale()[0] or locale.getdefaultlocale()[0]
    return lang or "en"



def get_i18n(language: str | None = None) -> I18n:
    return I18n(language or detect_language())
