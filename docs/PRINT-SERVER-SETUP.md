# Office print server + shared printer (best fix)

This is the **recommended** setup: **one Windows PC** hosts the printer queue, **all laptops print to that shared queue**, and the **print agent runs only on that PC**. Every job appears in the Windows spooler on the server, so the agent can send full details to your dashboard.

**You do not install the agent on customer laptops.**

---

## 0. What you need

| Item | Notes |
|------|--------|
| **Print server PC** | A Windows 10/11 PC that stays on during office hours (can be the “admin” laptop). |
| **Printer** | HP Smart Tank (or any printer) reachable on the LAN (e.g. `192.168.1.131`). |
| **Same Wi‑Fi** | Print server and all laptops on the same office network (same SSID/VLAN is simplest). |
| **This repo** | `print-agent` folder on the print server PC for config + Windows service. |

---

## 1. Prepare the print server PC

1. Sign in to the PC you will use as the **only** print host.
2. Note the **computer name**:
   - **Settings → System → About → Device name**  
   - Example: `CKP-PRINT-01` (avoid spaces; you can rename and reboot once).

3. Set a **fixed IP** for this PC on the router (DHCP reservation), or note its current IP. Clients can use `\\COMPUTERNAME\...` which is easier than IP.

---

## 2. Install the printer on the print server (TCP/IP to the HP)

1. **Settings → Bluetooth & devices → Printers & scanners → Add printer**.
2. If the HP does not appear automatically, choose **Add manually**.
3. Select **Add a printer using an IP address or hostname**.
4. **Device type:** TCP/IP device.  
   **Hostname or IP:** `192.168.1.131` (your printer’s IP from the printer report).  
   **Port name:** leave default. **Uncheck** “Query the printer and automatically select the driver” if the wizard mis-detects; pick **HP** and **Smart Tank 660-670** (or closest model) when prompted.
5. Finish until the printer shows under **Printers & scanners** with a normal name, e.g. `HP Smart Tank 660-670`.

---

## 3. Share the printer (critical)

1. **Settings → Bluetooth & devices → Printers & scanners**.
2. Click your HP printer → **Printer properties** (or **Manage → Printer properties**).
3. Open the **Sharing** tab.
4. Check **Share this printer**.
5. **Share name:** keep it short, no spaces, e.g. `HPCKP` (remember this).
6. Optionally check **Render print jobs on client computers** (can reduce server load; either way works for tracking).
7. Click **OK**.

---

## 4. Turn on network discovery and file/printer sharing

On the **print server PC**:

1. Open **Control Panel → Network and Internet → Network and Sharing Center → Change advanced sharing settings**.
2. Expand **Private** (current profile).
3. Turn on **Network discovery** and **File and printer sharing**.
4. Save.

**Windows Firewall** (if laptops cannot see the printer):

1. **Control Panel → Windows Defender Firewall → Allow an app through firewall**.
2. Ensure **File and Printer Sharing** is allowed on **Private** (and Guest/Public only if you truly use that profile—prefer Private for office Wi‑Fi).

---

## 5. Add the shared printer on each laptop (one-time per laptop)

On **each** laptop that should be tracked:

1. **Settings → Bluetooth & devices → Printers & scanners → Add device → Add manually**.
2. **Select a shared printer by name**.
3. Enter the UNC path:

   ```text
   \\PRINT-SERVER-COMPUTER-NAME\SHARE-NAME
   ```

   Example:

   ```text
   \\CKP-PRINT-01\HPCKP
   ```

   Use the **exact** device name from step 1 and **exact** share name from step 3.

4. If Windows asks for credentials, use a **local account on the print server** that has permission to print, or ensure **Guest** access is not required (domain/workgroup policies vary—simplest is same workgroup and password-protected sharing off for Private network only in small offices, or create a dedicated “print” user).

5. **Set as default** (optional): **Manage → Set as default** so new prints go to the shared queue.

6. **Remove or unpublish the old direct printer** (e.g. `HP12607E.lan`) so users do not accidentally print around your server:
   - **Printers & scanners → old printer → Remove**  
   Or leave it but train staff to use **CKP-PRINT** only.

---

## 6. Verify the queue is on the server

- On the **print server**, open **Settings → Printers & scanners → your shared HP → Open queue** while someone prints from a laptop.
- You must see **jobs listed in this queue**. If jobs only appear on the laptop and never here, laptops are still printing direct to the printer—fix the UNC path or default printer.

---

## 7. Install the print agent **only** on the print server

1. Copy or clone this repo on the print server PC.
2. Configure `print-agent/config.yaml`:

   ```yaml
   api_base_url: https://YOUR-BACKEND.onrender.com/api
   api_key: YOUR_AGENTS_SAME_AS_RENDER_AGENT_API_KEY
   poll_interval_seconds: 1.5
   printer_whitelist: []   # all printers on this PC; or list share name queue if needed
   ```

3. Test manually:

   ```powershell
   cd print-agent
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   py -m src.agent
   ```

4. Print from a laptop to `\\SERVER\HPCKP`. Within a couple of seconds you should see log lines and the **dashboard** should show the job.

5. Production: install the **Windows service** (see `print-agent/README.md` → **Run as a Windows Service**):

   ```powershell
   cd print-agent
   service\install_service.bat
   ```

---

## 8. Optional: reduce “direct to printer” bypass

If you control the **office router**, you can reserve `192.168.1.131` for the printer only and **block TCP port 9100** (raw JetDirect) from the **guest Wi‑Fi** to the printer, while allowing the **print server PC’s MAC** to reach the printer. That forces traffic through the server. Exact steps depend on router brand; skip if you are not comfortable with firewall rules.

---

## 9. One-line summary for staff or a wall sign

> **Office printer:** `\\YOUR-SERVER-NAME\HPCKP` — add this printer once in Windows.

---

## Troubleshooting

| Problem | What to check |
|---------|----------------|
| `\\SERVER\SHARE` not found | Same Wi‑Fi, network discovery on, firewall, correct spelling of computer + share name. |
| Prompts for password | User account on server or disable password-protected sharing (Private only) per your IT policy. |
| Dashboard empty | Agent running on **server** only; jobs visible in **server** print queue. |
| Wrong user name in logs | Windows reports the **user session on the print server** for some paths; remote job owner may show as guest or server user depending on driver—this is a Windows sharing limitation; still better than no central queue. |

For deployment with Render + Neon + Netlify, continue with [`DEPLOYMENT.md`](DEPLOYMENT.md) section 4 after the print path above works.
