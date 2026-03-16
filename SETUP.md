# XKG Mobile - Setup Guide

## Running XKG

Before using XKG Mobile, you need XKG running on your computer or server.

### Option 1: Local (Your Computer)

```bash
cd x-knowledge-graph
python main.py
```

XKG will start at: `http://localhost:5000`

### Option 2: VPS/Remote Server

Run XKG on your VPS at: `http://YOUR_SERVER_IP:5000`

---

## Connecting XKG Mobile

### 1. Start XKG

Make sure XKG is running first!

### 2. Open XKG Mobile

Launch the app on your phone.

### 3. Configure Endpoint

1. Tap the **Settings** ⚙️ icon (top right)
2. Enter your XKG endpoint:
   - **Local:** `http://localhost:5000` (if phone and computer on same network)
   - **Local network:** `http://192.168.1.x:5000` (find your computer's IP)
   - **Remote:** `http://YOUR_VPS_IP:5000`
3. Tap **Save**

### 4. Test Connection

Tap **Test** to verify the connection works.

---

## Finding Your Computer's IP Address

### Windows:
```cmd
ipconfig
```
Look for "IPv4 Address" — usually `192.168.1.x`

### For local network access:
- Make sure your phone is on the same WiFi as your computer
- Windows Firewall may need to allow the connection

---

## Using XKG Mobile

### Home Screen
- Tap any AI chatbot to open it in the app
- Use the search bar to search your XKG knowledge base

### Custom Apps
- Tap **+** to add your own chatbots/URLs

### Settings
- Configure XKG endpoint
- Test connection

---

## Troubleshooting

### "Connection failed"
- Is XKG running?
- Check the endpoint is correct
- Make sure phone and computer on same network
- Check Windows Firewall

### "No results"
- Import some content into XKG first
- Check XKG is running

---

## Network Setup Tips

For phone to connect to computer:

1. **Same WiFi** — phone and computer on same network
2. **Find your IP:** `ipconfig` on Windows → look for IPv4
3. **Use IP instead of localhost:** `http://192.168.1.100:5000`
4. **Firewall:** May need to allow Flutter through Windows Firewall
