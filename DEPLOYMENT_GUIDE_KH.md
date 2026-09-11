# មគ្គុទ្ទេសក៍ណែនាំការ Hosting ប្រព័ន្ធ E-Power Cambodia ទៅកាន់ Internet (Production Deployment Guide)

ឯកសារនេះរៀបចំឡើងដើម្បីណែនាំលោកអ្នកអំពីវិធីសាស្រ្ត Hosting គេហទំព័រ/ប្រព័ន្ធគ្រប់គ្រងអគ្គិសនី **E-Power Cambodia** ទៅកាន់ **Internet** ឱ្យដំណើរការបានជាសាធារណៈពីគ្រប់ទីកន្លែងជុំវិញពិភពលោក (តាមទូរសព្ទដៃ កុំព្យូទ័រ ឬ Tablet)។

---

## តារាងមាតិកា (Table of Contents)
1. [ឯកសារ និងប្រព័ន្ធដែលបានរៀបចំរួចជាស្រេចក្នុង Project](#១-ឯកសារ-និងប្រព័ន្ធដែលបានរៀបចំរួចជាស្រេច)
2. [វិធីទី ១៖ Hosting លើ Cloud ឥតគិតថ្លៃ ២៤/៧ (Render.com / Railway.app)](#វិធីទី-១-cloud-hosting-ឥតគិតថ្លៃ-២៤៧-rendercom-ណែនាំបំផុត)
3. [វិធីទី ២៖ បើកឱ្យចូលមើលលើ Internet ភ្លាមៗពីកុំព្យូទ័រ (Cloudflare Tunnel / Ngrok)](#វិធីទី-២-បើកឱ្យចូលមើលលើ-internet-ភ្លាមៗពីកុំព្យូទ័រ-cloudflare-tunnel--ngrok)
4. [វិធីទី ៣៖ Hosting លើ VPS ផ្ទាល់ខ្លួន (Ubuntu Linux / DigitalOcean / AWS / Linode)](#វិធីទី-៣-hosting-លើ-vps-ផ្ទាល់ខ្លួន-ubuntu-linux-ជាមួយ-docker--domain)
5. [ការគ្រប់គ្រង និងសុវត្ថិភាពទិន្នន័យ (SQLite Backup & Security)](#៥-ការគ្រប់គ្រង-និងសុវត្ថិភាពទិន្នន័យ)

---

## ១. ឯកសារ និងប្រព័ន្ធដែលបានរៀបចំរួចជាស្រេច

Project E-Power ត្រូវបានរៀបចំឯកសារស្តង់ដារ Cloud & Container រួចរាល់ ១០០%៖
* [`requirements.txt`](file:///d:/IT/E-Power/requirements.txt) ៖ បញ្ជីកញ្ចប់បណ្ណាល័យ Python (`fastapi`, `uvicorn`, `jinja2`, `qrcode`, `pillow`, `pydantic`...) សម្រាប់ឱ្យ Cloud Server ដំឡើងស្វ័យប្រវត្តិ។
* [`Procfile`](file:///d:/IT/E-Power/Procfile) ៖ ពាក្យបញ្ជាចាប់ផ្តើម Server លើ Render, Railway, ឬ Heroku (`web: uvicorn web_app:app --host 0.0.0.0 --port ${PORT:-8000}`)។
* [`render.yaml`](file:///d:/IT/E-Power/render.yaml) ៖ Blueprint សម្រាប់ចុច Deploy លើ Render.com ជាមួយ Persistent Disk ការពារកុំឱ្យបាត់ទិន្នន័យ SQLite។
* [`Dockerfile`](file:///d:/IT/E-Power/Dockerfile) ៖ កូដបង្កើត Docker Container ស្តង់ដារ (Python 3.11-Slim) ដំណើរការបានលើគ្រប់ Cloud Provider។
* [`docker-compose.yml`](file:///d:/IT/E-Power/docker-compose.yml) ៖ សម្រាប់ Deploy លើ VPS ឬ Server ផ្ទាល់ខ្លួន ដោយប្រើពាក្យបញ្ជាតែ ១ ជួរ (`docker compose up -d`)។
* [`.env.example`](file:///d:/IT/E-Power/.env.example) ៖ គំរូ Environment Variables (Port, Host, Database Path, Secret Key)។
* [`.gitignore`](file:///d:/IT/E-Power/.gitignore) និង [`.dockerignore`](file:///d:/IT/E-Power/.dockerignore) ៖ ការពារកុំឱ្យ Upload ឯកសារ Log និងឯកសារបណ្តោះអាសន្ន។

---

## វិធីទី ១៖ Cloud Hosting ឥតគិតថ្លៃ ២៤/៧ (Render.com) [ណែនាំបំផុត ⭐⭐⭐⭐⭐]

**Render.com** គឺជាសេវាកម្ម Cloud ដ៏ពេញនិយមបំផុត ដែលអនុញ្ញាតឱ្យលោកអ្នក Hosting Python FastAPI Application បាន**ឥតគិតថ្លៃ** ដំណើរការ **២៤ ម៉ោងលើ ២៤ ម៉ោង** ដោយមិនចាំបាច់បើកកុំព្យូទ័រចោលឡើយ ព្រមទាំងទទួលបាន **Public HTTPS Link** (ឧទាហរណ៍៖ `https://epower-cambodia.onrender.com`)។

### ជំហានទី ១៖ បង្កើតគណនី GitHub និង Upload Project
1. ចូលទៅកាន់ [github.com](https://github.com) រួចចុះឈ្មោះគណនី (បើមិនទាន់មាន)។
2. ចុចប៊ូតុង **New Repository** ៖
   - ដាក់ឈ្មោះ Repository (ឧទាហរណ៍៖ `epower-cambodia`)
   - ជ្រើសរើស **Public** ឬ **Private** (ណែនាំ Private ដើម្បីសុវត្ថិភាពទិន្នន័យ)
   - ចុច **Create repository**
3. Upload កូដទាំងអស់ពី Folder `d:\IT\E-Power` ឡើងទៅកាន់ GitHub (អាចប្រើ GitHub Desktop ឬអូសទម្លាក់ Upload files ដោយផ្ទាល់តាម Browser)។

### ជំហានទី ២៖ ភ្ជាប់ និង Deploy លើ Render.com
1. ចូលទៅកាន់ [render.com](https://render.com) រួចចុះឈ្មោះចូលប្រើ (Sign Up with GitHub)។
2. នៅលើ Dashboard ចុចប៊ូតុង **New +** នៅជ្រុងខាងស្តាំលើ -> ជ្រើសរើស **Web Service**។
3. ជ្រើសរើស **Build and deploy from a Git repository** -> ចុច Connect លើ Repository `epower-cambodia` របស់អ្នក។
4. បំពេញព័ត៌មានកំណត់ប្រព័ន្ធដូចខាងក្រោម៖
   - **Name:** `epower-cambodia` (ឬឈ្មោះតាមចិត្ត)
   - **Region:** `Singapore` (ជិតប្រទេសកម្ពុជាបំផុត ល្បឿនលឿន)
   - **Branch:** `main` (ឬ `master`)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn web_app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. **សំខាន់បំផុត (ការរក្សាទុកទិន្នន័យ Database):**
   - រំកិលចុះក្រោមត្រង់ **Advanced** -> **Disks** -> ចុច **Add Disk**
   - **Name:** `epower-data`
   - **Mount Path:** `/var/data`
   - **Size:** `1 GB` (រក្សាទុកវិក្កយបត្រ និងអតិថិជនបានរាប់សែននាក់)
   - ត្រង់ **Environment Variables** បន្ថែម៖
     - `DATABASE_PATH` = `/var/data/electricity_system.db`
     - `PYTHON_VERSION` = `3.11.9`
6. ចុចប៊ូតុង **Create Web Service**!
   - ប្រព័ន្ធនឹងចាប់ផ្តើម Install និង Deploy ដោយស្វ័យប្រវត្តិក្នងរយៈពេល ២-៣ នាទី។
   - នៅពេលដំណើរការចប់ លោកអ្នកនឹងទទួលបាន Link ផ្លូវការ (ឧ. `https://epower-cambodia.onrender.com`) ដែលអាចបើកមើលបានភ្លាមៗពីគ្រប់ទូរសព្ទដៃ និងកុំព្យូទ័រលើពិភពលោក!

---

## វិធីទី ២៖ បើកឱ្យចូលមើលលើ Internet ភ្លាមៗពីកុំព្យូទ័រ (Cloudflare Tunnel / Ngrok) [លឿនបំផុត ត្រឹមតែ ១ នាទី ⚡]

ប្រសិនបើលោកអ្នកចង់ឱ្យអតិថិជន ឬថ្នាក់លើចូលមើល និងសាកល្បងប្រើប្រាស់នៅលើ Internet ភ្លាមៗ **ដោយមិនបាច់ Upload កូដទៅណាឡើយ** និង**មិនបាច់ចំណាយលុយ**៖

### ជម្រើស A: ប្រើប្រាស់ Cloudflare Tunnel (ឥតគិតថ្លៃ ១០០% គ្មានកំណត់ម៉ោង)
1. ទាញយកកម្មវិធីតូចមួយ `cloudflared.exe` ពី Cloudflare៖
   - Link: [https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe)
   - ដាក់ឈ្មោះវាថា `cloudflared.exe` រួចដាក់ក្នុង Folder `d:\IT\E-Power`។
2. បើកដំណើរការប្រព័ន្ធ E-Power របស់អ្នកជាធម្មតា (ចុច `run.bat`)។
3. បើក CMD ក្នុង Folder E-Power រួចវាយពាក្យបញ្ជា៖
   ```cmd
   cloudflared tunnel --url http://localhost:8000
   ```
4. ប្រព័ន្ធនឹងផ្តល់ជូន Link សាធារណៈភ្លាមៗ (ឧទាហរណ៍៖ `https://random-words.trycloudflare.com`)។
5. គ្រាន់តែចម្លង Link នោះផ្ញើឱ្យអ្នកណាក៏ដោយ ពួកគេអាចចូលប្រើប្រាស់ប្រព័ន្ធ E-Power របស់អ្នកលើ Internet បានភ្លាមៗ!

### ជម្រើស B: ប្រើប្រាស់ Ngrok
1. ទាញយក Ngrok ពី [ngrok.com](https://ngrok.com)។
2. វាយពាក្យបញ្ជា៖
   ```cmd
   ngrok http 8000
   ```
3. ទទួលបាន HTTPS URL សម្រាប់ចែករំលែកលើ Internet ភ្លាមៗ។

---

## វិធីទី ៣៖ Hosting លើ VPS ផ្ទាល់ខ្លួន (Ubuntu Linux ជាមួយ Docker & Domain) [សម្រាប់កម្រិតក្រុមហ៊ុន Enterprise 🏢]

ប្រសិនបើក្រុមហ៊ុនរបស់អ្នកចង់បាន Domain ផ្លូវការផ្ទាល់ខ្លួន (ឧទាហរណ៍៖ `https://billing.epower.com.kh`) ដំណើរការលើ Server ផ្ទាល់ខ្លួន (DigitalOcean, AWS Lightsail, Linode, Contabo)៖

### ជំហានទី ១៖ ភ្ជាប់ទៅកាន់ VPS (SSH)
```bash
ssh root@YOUR_SERVER_IP
```

### ជំហានទី ២៖ ដំឡើង Docker និង Git
```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose git
systemctl enable --now docker
```

### ជំហានទី ៣៖ Clone ឬ Copy Project មកកាន់ Server
```bash
cd /opt
git clone https://github.com/your-username/epower-cambodia.git
cd epower-cambodia
```

### ជំហានទី ៤៖ ចាប់ផ្តើមប្រព័ន្ធជាមួយ Docker Compose
```bash
docker compose up -d --build
```
ប្រព័ន្ធ E-Power នឹងចាប់ផ្តើមដំណើរការលើ Port `8000` ដោយមាន persistent volume រក្សាទុកទិន្នន័យរឹងមាំជានិច្ច ទោះបី Restart Server ក៏មិនបាត់បង់ទិន្នន័យឡើយ។

### ជំហានទី ៥៖ កំណត់ Domain & SSL ដោយឥតគិតថ្លៃជាមួយ Nginx & Certbot
1. ដំឡើង Nginx & Certbot:
   ```bash
   apt install -y nginx certbot python3-certbot-nginx
   ```
2. បង្កើត Configuration ក្នុង `/etc/nginx/sites-available/epower`:
   ```nginx
   server {
       server_name billing.epower.com.kh;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
3. បើកដំណើរការ Site & ដំឡើង SSL:
   ```bash
   ln -s /etc/nginx/sites-available/epower /etc/nginx/sites-enabled/
   nginx -t
   systemctl reload nginx
   certbot --nginx -d billing.epower.com.kh
   ```
រួចរាល់! គេហទំព័ររបស់អ្នកនឹងមានសញ្ញាសោរសុវត្ថិភាព `https://` ស្របតាមស្តង់ដារអន្តរជាតិ។

---

## ៥. ការគ្រប់គ្រង និងសុវត្ថិភាពទិន្នន័យ

1. **ការ Backup Database:**
   - នៅក្នុង Sidebar របស់ប្រព័ន្ធ E-Power មានប៊ូតុង **«Backup Database»** ដែលអនុញ្ញាតឱ្យ Admin ទាញយកច្បាប់ចម្លងនៃ `electricity_system.db` មកទុកក្នុងកុំព្យូទ័របានគ្រប់ពេល។
2. **គណនី Admin អចិន្ត្រៃយ៍:**
   - គណនី `admin` / `admin123` ត្រូវបានការពារជាអចិន្ត្រៃយ៍ក្នុងប្រព័ន្ធ។ នៅពេលដាក់លើ Internet សូមចូលទៅកាន់ទំព័រ Profile ឬ Users ដើម្បីប្តូរពាក្យសម្ងាត់ឱ្យកាន់តែរឹងមាំ (ឧ. `Admin@EPower#2026!`)។
3. **Session & Security:**
   - Session Token ទាំងអស់ត្រូវបានផ្ទុកក្នុង Database ដោយមានកាលបរិច្ឆេទផុតកំណត់ច្បាស់លាស់ ធានាសុវត្ថិភាពខ្ពស់ក្នុងការប្រើប្រាស់តាម Internet។
