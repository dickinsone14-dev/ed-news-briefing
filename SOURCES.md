# The Daily Brief — Approved Sources

**Locked: 2026-05-04.** This is the **exclusive** list of sources permitted for morning and evening briefing research. Do not pull from anything not on this list. Cross-reference at least 2 approved sources before including a story.

---

## Wire services
- Reuters
- AP (Associated Press)
- AFP (Agence France-Presse)
- Bloomberg

## UK news
- BBC
- Financial Times
- The Telegraph (Daily + Sunday)
- The Times + Sunday Times
- The Guardian
- The Independent
- The Economist
- Sky News
- ITV News
- Channel 4 News

## US news
- CNN
- CNBC
- NBC News
- CBS News
- ABC News
- NPR
- Washington Post
- Wall Street Journal
- New York Times

## European news
- Le Monde
- FAZ (Frankfurter Allgemeine Zeitung)
- El País
- Irish Times

## Middle East
- Al Jazeera
- Times of Israel — **newsroom only, no blog content**
- Iran International — **facts only, never reflect editorial bias, cross-reference required**

## Russia / Ukraine
*No specialist regional outlets approved. Coverage via wire services, tier-1 UK/US outlets, and the defence specialists below (especially ISW for daily campaign assessments and Bellingcat for OSINT verification).*

## Specialist defence / military
- Janes — defence intelligence (gold standard)
- ISW — Institute for the Study of War (daily Russia/Ukraine campaign assessments)
- Bellingcat — OSINT verification, weapons ID, geolocation
- RUSI — Royal United Services Institute (UK strategic analysis)
- Defense News — US Pentagon procurement and policy

## Government / official primary sources

**UK:**
- gov.uk
- parliament.uk
- committees.parliament.uk
- Hansard
- bankofengland.co.uk
- ons.gov.uk
- HM Treasury
- OBR (Office for Budget Responsibility)

**US:**
- whitehouse.gov
- state.gov
- defense.gov
- CENTCOM
- Federal Reserve

**International institutions:**
- IAEA
- IMF
- World Bank
- OECD
- ECB
- Eurostat
- consilium.europa.eu (EU Council)
- NATO

> **Caveat:** "Official" ≠ "neutral observer." A Pentagon assessment of Russian losses is the *US government position*, not an independent fact. Use these as primary sources for **their own** statements, data, and policy. For claims about adversaries, cross-reference with wire services or specialist outlets.

## Polling
- YouGov
- Opinium
- Ipsos
- Survation
- More in Common
- Electoral Calculus *(forecasting/seat projections, not polling)*

## Economic think tanks
- Chatham House
- IFS — Institute for Fiscal Studies
- Resolution Foundation

## Real estate / housing
- Land Registry — actual transaction prices
- ONS House Price Index

## Markets / finance data
- Yahoo Finance
- Morningstar
- MarketWatch
- S&P Global PMI
- Trading Economics — **data only, no predictions or forecasts**
- Investing.com — **data terminal only, never as a news source**

## Industry / trade bodies
- BMA — British Medical Association — **medical/clinical data only, not opinions or advocacy**
- Trussell Trust — **operational data only (food parcel numbers, distribution stats)**
- RAC — **motoring data only**
- AA — **motoring data only**

---

## Banned sources (never use)
- Wikipedia
- Pravda-branded outlets (all variants)
- GB News
- Fox News
- Middle East Eye
- OilPrice.com
- Unverified social media
- Blogs without editorial oversight

---

## Approved domains (machine-readable — used by validate-index.py)

Edit only between the `BEGIN` / `END` markers below. The pre-commit hook reads this list and fails any commit where `index.html` contains a hyperlink inside a curated edition pointing to a domain not on this list. To add a new outlet to the approved set: add it to the prose section above AND add its domain(s) here.

<!-- BEGIN APPROVED DOMAINS -->
# Wire services
reuters.com
apnews.com
ap.org
afp.com
bloomberg.com

# UK news
bbc.co.uk
bbc.com
ft.com
telegraph.co.uk
thetimes.com
thetimes.co.uk
theguardian.com
guardian.co.uk
independent.co.uk
economist.com
news.sky.com
sky.com
itv.com
channel4.com

# US news
cnn.com
edition.cnn.com
cnbc.com
nbcnews.com
cbsnews.com
abcnews.com
abcnews.go.com
npr.org
washingtonpost.com
wsj.com
nytimes.com

# European news
lemonde.fr
faz.net
elpais.com
irishtimes.com

# Middle East
aljazeera.com
timesofisrael.com
iranintl.com

# Specialist defence / military
janes.com
understandingwar.org
bellingcat.com
rusi.org
defensenews.com

# Government / official — UK
gov.uk
parliament.uk
hansard.parliament.uk
committees.parliament.uk
bankofengland.co.uk
ons.gov.uk
obr.uk

# Government / official — US
whitehouse.gov
state.gov
defense.gov
centcom.mil
federalreserve.gov

# International institutions
iaea.org
imf.org
worldbank.org
oecd.org
ecb.europa.eu
ec.europa.eu
europa.eu
consilium.europa.eu
nato.int

# Polling
yougov.com
yougov.co.uk
opinium.com
opinium.co.uk
ipsos.com
survation.com
moreincommon.com
electoralcalculus.co.uk

# Economic think tanks
chathamhouse.org
ifs.org.uk
resolutionfoundation.org

# Real estate / housing — already covered by gov.uk and ons.gov.uk

# Markets / finance data
finance.yahoo.com
uk.finance.yahoo.com
morningstar.com
marketwatch.com
spglobal.com
tradingeconomics.com
investing.com

# Industry / trade bodies
bma.org.uk
trussell.org.uk
rac.co.uk
theaa.com

# Our own site
thedailybrief.co.uk

<!-- END APPROVED DOMAINS -->
