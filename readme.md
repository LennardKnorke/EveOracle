# EveOracle 👁️

> Real-time tactical intelligence, roster management, and matchup analysis for **EVE Online**.

EveOracle is a combat companion dashboard designed for Fleet Commanders (FCs), scouts, and pilots. It ingests active fleet data and local chat pastes, resolves standings and affiliations, and pulls deep combat telemetry from zKillboard to provide instant threat assessment and comparative matchup analytics.

---

## 🛠️ Tech Stack

### **Frontend**
* **Framework:** React 18 (Vite, TypeScript)
* **Routing & State:** React Router DOM v6, Context API
* **UI/UX:** Custom modular CSS with a dark sci-fi theme, HTML5 Drag-and-Drop
* **Media Assets:** CCP Image Server (`images.evetech.net`)

### **Backend & Services**
* **API Framework:** FastAPI (Python 3.12, Uvicorn, Pydantic v2)
* **Database:** MySQL 8.4 with asynchronous connection pooling (`aiomysql`, SQLAlchemy 2.0)
* **Background Worker:** Python-based scheduled worker for background processing and data hydration
* **Static Data (SDE):** Pre-parsed Static Data Exports (`ships.json`) served via static mounts
* **Containerization:** Fully containerized with Docker & Docker Compose

---

## ⚡ Current Features

### 1. Authentication & Ingestion
* **EVE SSO Integration:** OAuth2 authentication supporting character identification and ESI scopes.
* **Dual Ingestion Engine:**
  * **Update Fleet:** Fetches active fleet members and their current ships directly via ESI.
  * **Paste Local Chat:** Fast multi-line name parsing with client/server deduplication to avoid redundant queries.

### 2. Tri-State Team Management (Allies, Neutrals, Enemies)
* **Automated Standings Sorting:** Automatically categorizes pilots into *Allies*, *Neutrals*, or *Enemies* using personal/corp/alliance standings hierarchy.
* **3-Tier Combat Entity Model:**
  * **(W1) Pilot Only:** Known pilot and zKillboard history, unknown ship.
  * **(W2) Pilot + Ship:** Pilot linked to an identified ship with a 2-row icon grid (Pilot + Ship on top, Corp + Alliance below).
  * **(W3) Ship Only:** Spotted ship on D-scan/grid without an identified pilot.
* **Interactive Token Operations:**
  * Drag-and-drop pilots and ships between columns or drop W1 onto W3 to merge them into W2 (retaining pilot standing).
  * Searchable ship selector modal to assign/change ships.
  * Pilot selector modal to link unassigned pilots to spotted ships.
  * Right-click ship detachment on W2 cards.

### 3. Tactical Matchup Dashboard
* **Side-by-Side Comparison:** Dedicated Allies and Enemies columns.
* **Compact Cards:** At-a-glance scanning of danger ratings, weekly K/D, average gang size (Solo vs. Blob), and current ship experience.
* **Expanded Combat Dossiers:** Clicking a card expands it to the full column:
  * **Context-Aware Ship Dossier:** Checks pilot history specifically on their currently flown hull (kills, losses, ISK destroyed in that ship).
  * **Multi-Timeframe Metrics:** All-Time vs. Last 30 Days vs. Weekly K/D and ISK efficiency.
  * **Operational Intel:** Top 5 ships flown and most frequent hunting solar systems.
  * Independent expansion per column with quick collapse back to list view.

---

## 🗺️ Planned Roadmap

- [ ] **Fleet Composition Breakdown:** Aggregate counter summary across Allies vs. Enemies (Logistics, Tackle, Heavy DPS, EWAR, Capitals).
- [ ] **Cyno & Bait Heuristics:** Automated scanning of lossmail fits to detect Cynosural Fields, Covert Cynos, and interdiction capabilities.
- [ ] **MySQL Cache Layer:** Persistent pilot telemetry caching in MySQL via the scheduled background worker to eliminate zKillboard rate-limit bottlenecks.
- [ ] **Live WebSocket Streaming:** Real-time updates for active fleet positioning and ship changes.
- [ ] **Machine Learning Matchup Engine (Long-Term):** Neural network models trained on composition matchups and historical engagements to predict fight outcomes.