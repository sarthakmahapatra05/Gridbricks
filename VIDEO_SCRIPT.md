# Video Walkthrough Script
## Gridbricks Energy — Wind Forecast Reliability & Day-Ahead Buying

- **Live Frontend:** [https://gridbricks-seven.vercel.app/](https://gridbricks-seven.vercel.app/)
- **Live Backend:** [https://gridbricks-9mcs.onrender.com](https://gridbricks-9mcs.onrender.com)
- **API Documentation:** [https://gridbricks-9mcs.onrender.com/docs](https://gridbricks-9mcs.onrender.com/docs)
- **Target Video Length:** 4–6 minutes

---

### Segment 1: Introduction & The Business Problem (~45 seconds)
**[On-screen: Browser showing https://gridbricks-seven.vercel.app/, scrolled to Section 01: Guidance & Buffer]**

> "Hello everyone. Welcome to the demonstration of Gridbricks Energy's **Wind Forecast Reliability Platform for Day-Ahead Power Buying**.
> 
> In wholesale electricity markets, power traders purchase electricity on Day $D-1$ before gate closure. If an energy trader relies on National Grid ESO's wind forecast and actual wind generation falls short, the utility is caught short in the Balancing Mechanism and faces steep cashout imbalance charges.
> 
> Our mission was to build an executive decision-support system that gives power traders the answer they need in under 5 seconds: **How much extra reserve buffer should they procure day-ahead?**, followed by transparent empirical evidence across all 744 settlement hours of January 2026."

---

### Segment 2: Architecture & Ingestion Streams (~45 seconds)
**[On-screen: Scroll to Section 04: Operational Context, highlighting the Methodology cards, and brief tab switch to Swagger docs]**

> "Before exploring the decision dashboard, let's look at the underlying architecture.
> 
> Our backend is built with **FastAPI** and **Python 3.11**, containerized via Docker and deployed live on Render, ingesting data directly from the official **Elexon BMRS API**:
> 1. `FUELHH`: Real settled actual wind generation across all 48 half-hour settlement periods per day.
> 2. `WINDFOR`: National Grid ESO's national wind generation forecasts, published at an hourly resolution.
> 
> Crucially, our calculation engine enforces a strict **anti-lookahead filter**: for delivery day $D$, we only select the most recent forecast revision published prior to the trader's cutoff on day $D-1$ (defaulting to 09:00 UK time). Any forecast published after cutoff is strictly excluded."

---

### Segment 3: Section 01 — Executive Decision & Buffer Guidance (~1 minute)
**[On-screen: Click '01 Guidance & Buffer' in top navbar or left sidebar]**

> "Let's begin where the trader starts: **Section 01 — Guidance & Buffer**.
> 
> In the top sticky navbar, you can see our 4 core views with real-time scroll-spy tracking. On the left is our dedicated 280px sidebar.
> 
> Look at the headline recommendation: **'Procure +1,852 MW Buffer (+16.0% Over Forecast)'**. 
> Power traders need the answer immediately. Based on January's error distribution, we advise holding an average buffer of approximately 1,852 MW and up to 5,329 MW on peak-error days.
> 
> Right beside it, we display the key KPIs for the selected delivery day: Mean Actual Generation, Decision Forecast, Mean Bias, and Mean Absolute Error.
> 
> Notice how changing the delivery date—either using the stepper buttons, the dropdown, or our scenario presets—instantly re-evaluates the entire day's profile."

---

### Segment 4: Section 02 — Delivery Day Profile (Actual vs. Forecast) (~1 minute 15 seconds)
**[On-screen: Click '02 Delivery Day Profile' or scroll down to the line chart]**

> "Scrolling to **Section 02 — Delivery Day Profile**, we see the full 48 half-hour settlement delivery timeline for the selected day.
> 
> Here are key engineering details implemented specifically for power market realities:
> 1. **Data Cadence & Resolution:** Actual generation (in blue) is reported half-hourly (48 periods). Forecasts (in orange) are published hourly (24 periods). Unforecasted `:30` half-hour slots are maintained as clean gaps without synthetic linear interpolation.
> 2. **Hourly Step Line:** The forecast is rendered as an hourly step line, accurately reflecting that an hourly forecast represents the entire hour block.
> 3. **Error Shading Layer:** We draw a custom SVG polygon between the actual curve and the forecast step line. Whenever orange sits above blue, the trader is over-forecasted and exposed to deficit risk.
> 4. **Auditability:** Hovering over any data point reveals a borderless tooltip displaying the exact MW outturn, the forecast, the net difference, and the exact forecast publish timestamp on Day $D-1$."

---

### Segment 5: Section 03 — 31-Day Benchmark & Systematic Bias (~1 minute)
**[On-screen: Click '03 31-Day Benchmark' or scroll down to the bar chart]**

> "In **Section 03 — 31-Day Benchmark**, we evaluate the model across the entire month of January 2026.
> 
> Each bar represents a delivery day's average bias. Amber bars indicate an over-forecast (forecast exceeded actuals), while emerald bars indicate under-forecast.
> 
> Notice that out of 31 days in January, **26 days were significantly over-forecasted**, demonstrating a persistent structural bias of **+1,852 MW (+16.0%)**.
> 
> The chart is fully interactive: clicking any bar—for example, **January 28th**, the largest miss of the month—instantly switches the delivery day profile in Section 02 to that date.
> 
> Below the chart, we summarize the monthly metrics: Mean Actual of 11,581 MW, Mean Forecast of 13,433 MW, MAE of 2,127 MW, and an RMSE of 2,606 MW across all 744 hourly verification points."

---

### Segment 6: Section 04 — Operational Context & Root Cause Analysis (~45 seconds)
**[On-screen: Scroll to Section 04: Operational Context]**

> "In **Section 04 — Operational Context**, we address the fundamental question: *Why does this bias exist?*
> 
> 1. **Timestamp Shift Correlation Test:** We ran a rigorous -2h to +2h time-shift correlation check on the dataset. The correlation peaks at +0.0 hours ($r = 0.9283$). This mathematically proves the bias is not caused by timezone misalignment (e.g. UTC vs GMT or BST).
> 2. **Bias Root Cause:** The persistent bias is likely explained by scope differences between `FUELHH` (which meters transmission-connected wind farms only) and `WINDFOR` (which may include embedded generation), or by grid curtailment where National Grid instructed wind farms to turn down output.
> 3. **Decision Cutoff Sensitivity:** Traders can test earlier or later decision cutoffs (e.g., 07:00, 09:00, 11:00, 12:00) using the left sidebar dropdown to assess how forecast accuracy evolves closer to gate closure."

---

### Segment 7: Mobile Responsiveness & Testing (~45 seconds)
**[On-screen: Open Chrome DevTools, toggle device emulation to iPhone 14 / 390px width]**

> "We also engineered this platform to be 100% mobile responsive for traders checking market conditions on the go:
> - Notice the sticky mobile header with quick day navigation.
> - Clicking the **Filters** button opens a smooth slide-out drawer providing full access to cutoff hours, calendar selection, and scenario presets.
> - The charts automatically adjust axis tick density to prevent text overlap.
> 
> On the engineering side, our codebase is backed by **10 out of 10 automated pytest tests** covering anti-lookahead logic, edge cases, missing data handling, and API schema validation, all packaged with a clean multi-stage Dockerfile and deployed continuously to Vercel and Render."

---

### Segment 8: Conclusion & Wrap-Up (~15 seconds)
**[On-screen: Switch back to full desktop view at the top of the dashboard]**

> "Thank you for watching! Gridbricks Energy provides power traders with instantaneous actionable buffer guidance, robust empirical benchmarks, and an intuitive modern trading interface.
> 
> The live web application is accessible at **https://gridbricks-seven.vercel.app/** and the backend API is live at **https://gridbricks-9mcs.onrender.com**. Thank you."
