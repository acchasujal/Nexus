
Below is the combined team document. You can give **Part A directly to Teammate 1's AI model and Part B directly to Teammate 2's AI model**.

---

# **NEXUS — FINAL SIH PRODUCT HARDENING & DEMO TRANSFORMATION PLAN**

## **Objective**

Transform NEXUS from a collection of technically strong intelligence modules into a coherent, realistic and investigator-usable criminal-network intelligence workspace.

The product must make this loop obvious:

NETWORK STATE  
    ↓  
NETWORK CHANGE  
    ↓  
WHY DID THIS APPEAR?  
    ↓  
EVIDENCE ASSESSMENT  
    ↓  
SUPPORTS / CONFLICTS / MISSING  
    ↓  
ABSTAIN OR SURFACE OPERATIONAL SIGNAL  
    ↓  
NEXT BEST VERIFICATION  
    ↓  
INVESTIGATOR DECISION  
    ↓  
GRAPH / CASE UPDATE  
    ↓  
NEW NETWORK SNAPSHOT  
    ↓  
AUDIT

Do not add features merely to make the prototype larger.

Prioritize:

1. USP clarity  
2. investigator usability  
3. evidence defensibility  
4. realistic operational workflow  
5. correctness  
6. performance  
7. domain/legal credibility  
8. visual polish

---

# **PART 1 — ADDITIONAL FINDINGS FROM THE REMAINING SCREENSHOTS**

These are the findings that became clearer from the additional screenshots and were not fully exposed in the earlier set.

---

## **A. Entity Fusion → Network Transformation Delta**

This is one of the strongest newly visible features.

The screen shows:

> Network Transformation Delta (What Changed)

with:

* entities merged & unified  
* cross-case bridge formed  
* evidentiary propagation  
* rewired edges  
* merged entities 8 → 4

### **Why this is important**

This is much stronger than a generic "entity merge" screen.

It visually proves that NEXUS is not simply finding a match.

It demonstrates:

entity-resolution decision  
        ↓  
network topology changes  
        ↓  
new cross-case relationship  
        ↓  
evidence propagates

That is a major part of the actual NEXUS thesis.

### **Problem**

The current screen still reads like a technical post-processing report.

An investigator needs:

> "What changed in my investigation because of this decision?"

### **Required change**

Rename/structure it as:

**Resolution Impact**

Show:

BEFORE  
8 record-level entities

DECISION  
2 records confirmed as same entity

AFTER  
7 canonical entities

NETWORK IMPACT  
\+1 cross-case bridge  
\+3 propagated relationships  
\+0 unsupported relationships

Then:

### **"Why this changed"**

Verified phone match  
\+ matching father name  
\+ address corroboration  
\+ investigator confirmation

And:

### **"What should I inspect?"**

Affected cases:  
FIR-2026-141  
FIR-2026-207

Affected evidence:  
4 records

Affected relationships:  
3

This should become a major demo moment.

---

# **B. Entity Fusion contradiction matrix is excellent — but needs one major improvement**

The new screen shows:

Corroborated Facts  
Discrepancies / Conflicts  
Unverified / Partial

This is very good.

This is actually more credible than simply showing an 86/100 match.

The judge can see:

Phone → corroborated  
Father name → corroborated  
Address → corroborated

Name → conflict  
DOB → conflict

### **Current problem**

The system still displays the top:

> EVIDENCE SIMILARITY 86/100

That makes the detailed contradiction matrix feel secondary.

It should be the opposite.

### **Change**

Make the primary assessment:

ENTITY RESOLUTION ASSESSMENT

Supporting signals: 3  
Conflicting signals: 3  
Unverified signals: 1

Decision:  
AMBIGUOUS — INVESTIGATOR REVIEW REQUIRED

Then show the individual evidence.

A numerical score can remain behind "technical details" if you truly need it, but it must not be the main decision.

---

# **C. Entity Fusion needs a conflict-aware decision gate**

Current:

Confirm Fusion  
Reject Match  
Defer Decision

This is good.

But the UI should explain why a decision is required.

For example:

3 corroborating facts  
3 conflicts  
1 unresolved field

Current recommendation:  
DEFER DECISION

Reason:  
Conflicting DOB and name prevent deterministic identity confirmation.

The system should never recommend "Confirm" merely because the score is high.

---

# **D. Entity Search exposes a major false-positive problem**

The screenshot shows:

Search:

> rajesh

Results:

* Rajesh Shetty — 85%  
* Rajesh Khan — 85%  
* Rajesh Bhat — 85%  
* Rajesh Verma — 85%

This appears to be driven heavily by:

> Word token match  
> full name  
> full name prefix

### **This is not realistic enough.**

If an investigator searches "Rajesh", returning many unrelated people with identical 85% scores looks like a simplistic string matcher.

### **Required change**

Entity Search must distinguish:

EXACT NAME MATCH  
PARTIAL NAME MATCH  
IDENTIFIER MATCH  
MULTI-FIELD CORROBORATION  
AMBIGUOUS

For:

> Rajesh

show:

Broad name query

4 name matches

No identity corroboration established.

Do not call them:

> MATCHED 85%

unless actual entity-resolution evidence exists.

Use:

> Name candidate

instead.

---

# **E. Entity Search should rank by evidence, not name similarity alone**

Preferred hierarchy:

Exact phone \+ name  
↓  
Exact identifier  
↓  
Name \+ father name \+ address  
↓  
Name \+ case overlap  
↓  
Name similarity only

If only the name matches:

Candidate match  
Confidence:  
Insufficient identity evidence

The investigator can then inspect.

---

# **F. Case-specific Network Graph is much more useful than Global Graph**

The additional screen showing:

> FIR-2026-236

with:

> Case Only / 1 Hop / 2 Hops / 3 Hops

is significantly more investigator-friendly than the huge global graph.

This should become the default network experience when an investigator is inside a case.

### **Preserve this pattern.**

Default:

Case Only

then:

1 Hop  
2 Hops  
3 Hops

rather than dumping the investigator into a 400+ node graph.

---

# **G. Case graph has a very good "Why is this entity shown?" pattern**

The sidebar shows:

> WHY IS THIS ENTITY SHOWN?

> Target investigation case FIR-2026-236

This should become a **global graph UX standard**.

Every node/edge should be explainable through:

Why shown?  
Distance from case  
Source records  
Authoritative path  
Evidence

This is exactly how to make graph analytics investigator-friendly.

---

# **H. Global Explorer and Case Explorer should be connected**

Current flow is conceptually:

Case graph  
→ Global Explorer

Good.

But the reverse should also work:

Global graph  
→ Open case context

with the relevant node/path preserved.

Never lose context during navigation.

---

# **I. Timeline is promising but currently too generic**

The new timeline screen has a strong structure:

FIR Registration  
Evidence Ingestion  
CDR & Banking Logs  
Entity Resolution  
Network Leads

This is useful.

But the current timeline mixes:

real investigative event  
system processing event  
data ingestion event  
analysis event

These should be separated.

---

# **J. Timeline needs event semantics**

Every event should have:

EVENT TYPE  
SOURCE  
OBSERVED TIME  
INGESTED TIME  
SYSTEM PROCESSING TIME  
ACTOR  
RELATED CASE  
RELATED EVIDENCE

For example:

14 Feb 2026  
CDR record observed

Source:  
CDR-A12

Observed:  
14 Feb 22:41

Ingested:  
16 Feb 10:03

Processed:  
16 Feb 10:04

This distinction is important in evidence-heavy systems.

---

# **K. Timeline should support "investigation change" mode**

Add:

All Events  
Investigative Changes  
Evidence  
Communications  
Transactions  
Entity Resolution

"Investigative Changes" should highlight:

Entity merged  
New relationship detected  
Signal generated  
Investigator confirmed  
Investigator dismissed  
Verification completed

This makes the timeline operational rather than simply chronological.

---

# **L. Similar Cases screen is currently too empty**

The screenshot shows:

> Similarity Match Dimensions

with:

* shared suspect network  
* shared phone call matches  
* shared registered address  
* shared forensic dependency

and then:

> 0 matches

### **Problem**

This looks like a feature that exists, but isn't providing useful information in the current case.

### **Better empty state**

Instead of:

> 0 matches

show:

No strong similar investigations found.

Compared:  
50 investigations

Threshold:  
≥ 65% structural similarity

Nearest structural match:  
52%

Primary reason similarity was not reached:  
No shared communication topology

That demonstrates that the engine actually searched.

---

# **M. Similar Case dimensions should become actual explanation dimensions**

If these are truly implemented:

Network structure  
Communication pattern  
Financial structure  
Geographic pattern  
Temporal pattern  
Entity overlap  
Evidence overlap

Then show them.

For example:

CASE SIMILARITY

Network structure       81%  
Communication          73%  
Financial structure    89%  
Geography              40%  
Temporal               67%

Overall structural similarity:  
71%

Only do this if these values are real calculations.

---

# **N. Similar Cases should connect directly to Case DNA**

Right now:

Case DNA

and:

Similar Cases & Patterns

feel like separate concepts.

They should become one workflow:

Current investigation  
↓  
Find structurally similar investigations  
↓  
Compare dimensions  
↓  
Inspect common evidence  
↓  
Inspect differences  
↓  
Open comparative graph

That would make Case DNA substantially more useful.

---

# **O. Investigation workspace is actually one of the best architectural patterns**

The new screenshot shows:

Investigation Overview  
Network Graph  
Event Timeline  
Similar Cases & Patterns  
Copilot

This is exactly the sort of context-preserving workflow NEXUS needs.

I would make this the core model.

Instead of forcing users to navigate between unrelated global screens:

Case  
→ Network  
→ Timeline  
→ Similar Cases  
→ Copilot

should all remain inside a persistent investigation context.

This is one of the most important additions from the new screenshots.

---

# **P. Generate Evidence Dossier is good — but needs structured grounding**

The new:

> Generate Evidence Dossier

button is highly valuable.

Do not make it just an LLM-generated report.

The dossier should contain:

Case summary  
Observed network changes  
Entities involved  
Verified relationships  
Supporting evidence  
Conflicting evidence  
Missing evidence  
Timeline  
Verification actions  
Similar cases  
Network snapshot  
Source provenance  
Decision history  
Audit references

Every finding should link back to evidence.

---

# **Q. Don't create a "legal conclusion" dossier**

The dossier should not say:

> Subject is guilty.

or:

> Criminal network established.

Instead:

Observed finding  
Evidence basis  
Assessment  
Uncertainty  
Investigator decision

This fits the product's evidence-grounded philosophy.

---

# **R. One new cross-screen issue: too many competing names for the same concepts**

Across screenshots:

Repeat Offender  
Repeat-Case Signal  
Repeat-Case Entity  
Known Offender  
Candidate Link  
Hard-ID Corroborated  
Confirmed  
Anomaly Detected  
Critical Review  
High Criticality  
Red Flag  
Evidence-backed

These need a common ontology.

---

# **COMBINED MASTER CHANGE LIST**

Now combining the previous screenshots \+ remaining screenshots, this is the actual final work backlog.

---

# **P0 — MUST FIX BEFORE DEMO**

### **1\. Fix document ingestion 404**

Current deployed:

/api/v1/documents → 404

Trace and repair full upload/ingestion flow.

---

### **2\. Fix document source validation**

PDF filename:

> Unit 1 — Introduction to Cloud Computing.pdf

cannot silently be treated as:

> FIR Document.

Add MIME/source-type validation.

---

### **3\. Make Intelligence Center the default entry point**

/login  
↓  
/intelligence  
↓  
Network Pulse  
---

### **4\. Make one investigation the central context**

Create persistent:

Investigation Context  
Case  
Network  
Timeline  
Evidence  
Similar Cases  
Copilot  
Verification  
Audit  
---

### **5\. Build real Network Change → Verification loop**

Must actually work:

Network Diff  
→ Pulse  
→ Evidence  
→ Verification Task  
→ Investigator decision  
→ Graph update  
→ New snapshot  
---

### **6\. Make Network Diff visible**

Show:

Before  
After  
Added edges  
Removed edges  
Changed identifiers  
New bridge  
---

### **7\. Make evidence assessment primary**

Replace unexplained:

94%  
91%  
86/100%

with:

Supporting  
Conflicting  
Missing  
Verified  
Independent sources  
Freshness  
Integrity

Scores can remain technical detail.

---

### **8\. Make abstention first-class**

Show:

ABSTAINED — INSUFFICIENT EVIDENCE

with:

What is known  
What is missing  
What would resolve it  
---

### **9\. Real Next Best Verification workflow**

Not just text.

Must support:

Create task  
Assign  
Pending  
Requested  
Received  
Reviewed  
Verified  
---

### **10\. Standardize signal states**

NEW  
REVIEWING  
VERIFICATION REQUIRED  
CONFIRMED  
DISMISSED  
STALE  
---

### **11\. Standardize evidence states**

SUPPORTS  
CONFLICTS  
MISSING  
INFERRED  
VERIFIED  
---

### **12\. Standardize identity resolution states**

CANDIDATE  
MATCH  
AMBIGUOUS  
UNRESOLVED  
NON-MATCH  
CONFIRMED  
---

### **13\. Remove dangerous/overclaiming language**

Avoid unless explicitly evidenced:

Repeat Offender  
Criminal Syndicate  
High Criticality  
Key Influencer  
Risk  
Threat  
Guilty  
Forecast  
Prediction

Prefer factual graph/evidence language.

---

### **14\. Remove implementation labels**

Delete:

P1-B  
P1-C  
P1-D  
P2  
---

### **15\. Fix investigator identity/persona**

Use one consistent investigator identity.

Avoid:

System Administrator  
ADMIN  
OFFICER-DEMO-ADMIN-01  
INVESTIGATOR

all appearing simultaneously.

---

### **16\. Fix legal terminology**

Do not use outdated CrPC Section 91 in a current BNSS workflow. BNSS Section 94 addresses summons/orders for production of documents and electronic communications. ([India Code](https://www.indiacode.nic.in/bitstream/123456789/21180/1/bharatiya_nagarik_suraksha_sanhita%2C_2023_1723877824_66c049c04ad7c_%281%29.pdf?utm_source=chatgpt.com))

Use current legal terminology only after verifying the exact procedure.

---

### **17\. Correct BSA UI wording**

BSA Section 63 includes the electronic-record certificate structure and hash information. ([India Code](https://www.indiacode.nic.in/bitstream/123456789/20063/1/a2023-47.pdf?utm_source=chatgpt.com))

Do not casually label the whole NEXUS audit screen:

> LEGAL CERTIFICATE

Use:

Electronic Evidence Integrity  
Section 63 Certificate Preparation  
Evidence Integrity Record

depending on what the implementation actually provides.

---

### **18\. Fix `null`, `undefined`, raw IDs and developer strings**

Especially:

District: null  
audit\_batch\_anchored  
copilot\_answered  
---

### **19\. Canonical identifier model**

Normalize:

case ID  
FIR ID  
entity ID  
source/evidence ID  
pulse ID  
lead ID  
verification task ID  
snapshot ID

Display human-readable identifiers; preserve canonical IDs internally.

---

# **P1 — PRIMARY PRODUCT/USP IMPROVEMENTS**

### **20\. Intelligence Center**

Default:

Network Pulse

with:

What changed?  
Why?  
Evidence?  
Uncertainty?  
Verification?  
---

### **21\. Root Intelligence Event**

Deduplicate:

Pulse  
Bridge  
Adaptation  
Repeat-case signal  
Hotspot  
Identity drift

when they originate from the same underlying structural change.

One root event:

INTELLIGENCE EVENT

with multiple analytical views.

This is important for avoiding alert fatigue.

---

### **22\. Affected Investigation routing**

Every signal should identify:

Affected cases  
Case owner  
District  
Status  
Why affected  
---

### **23\. Cross-district coordination workflow**

Add:

District A  
District B  
Shared intelligence  
Open verification items  
Responsible officers  
Coordination state  
---

### **24\. Case Investigation Workspace**

Use the new screen pattern:

Overview  
Network  
Timeline  
Similar Cases  
Copilot  
Evidence  
Verification  
Audit  
---

### **25\. Contextual Network Explorer**

Opening the graph from Pulse/Case/Entity must preserve:

case  
snapshot  
selected entity  
selected edges  
timeline  
evidence  
signal  
---

### **26\. Case graph defaults**

Use:

Case Only  
1 Hop  
2 Hops  
3 Hops

rather than global 400+ node views.

---

### **27\. Global graph remains for cross-case analysis**

Use global graph only when needed.

---

### **28\. Edge inspection**

Every important edge should expose:

Relationship type  
Source  
Date  
Observed value  
Evidence  
Integrity  
Freshness  
---

### **29\. "Why is this entity shown?"**

Standardize everywhere.

---

### **30\. "Why did this appear?"**

Standardize for every intelligence signal.

---

### **31\. Identity Drift**

Show:

Previous identifier  
New identifier  
Observed date  
Source  
Corroboration  
Resolution state  
---

### **32\. Network Adaptation**

Make:

Previous network  
Changed relationship  
Replacement path  
Evidence  
Verification

the core presentation.

This is one of your strongest capabilities.

---

### **33\. Entity Fusion**

Show:

supporting factors  
conflicts  
unverified factors  
decision

rather than making 86/100 the headline.

---

### **34\. Entity Search**

Change broad name results from:

MATCHED 85%

to:

Name candidate

unless actual corroboration exists.

---

### **35\. Entity Search ranking**

Prioritize:

identifier corroboration  
multi-field corroboration  
cross-case evidence  
name similarity

in that order.

---

### **36\. Repeat-case intelligence**

Rename:

Repeat-Offender Detection

to:

Cross-Case Entity Recurrence

or:

Repeat-Case Entity Signals  
---

### **37\. Case DNA / Similar Cases integration**

Create:

Find similar investigations  
→ compare dimensions  
→ inspect evidence  
→ compare networks  
---

### **38\. Similar-case empty state**

Do not simply show:

> 0 matches.

Show:

Compared N investigations  
Threshold N  
Closest match  
Why threshold was not reached  
---

### **39\. Case DNA explanation**

Expose actual dimensions rather than:

> Harmonic vector average.

---

### **40\. Investigation dossier**

Add structured:

> Generate Evidence Dossier

with source references.

---

# **P1 — DATA/EVIDENCE REALISM**

### **41\. Data profile indicator**

Use:

NCRB-calibrated synthetic demonstration dataset

or equivalent.

Never imply individual-level NCRB records if they are synthetic.

---

### **42\. Evidence lineage**

Implement visually:

Source  
→ Ingestion  
→ Hash  
→ Extraction  
→ Entity resolution  
→ Graph relation  
→ Intelligence signal  
→ Investigator decision  
---

### **43\. Source quality**

Separate:

Authenticity  
Freshness  
Completeness  
Corroboration  
Resolution

instead of one generic score.

---

### **44\. Legacy evidence**

Show:

LEGACY — NOT HASH-SEALED

rather than only:

> Hash not available.

---

### **45\. Evidence conflicts**

Create explicit conflicting evidence examples.

---

### **46\. Evidence freshness**

Every major signal should display:

Observed  
Updated  
Snapshot  
Freshness  
---

# **P1 — INVESTIGATOR PRODUCTIVITY**

### **47\. Worklist**

Add:

Next action  
Evidence gap  
Last intelligence change  
Owner  
Open verification task  
---

### **48\. Investigation assignment**

Add:

Owner  
Team  
Priority  
Status  
Due date  
---

### **49\. Decision log**

Store:

Decision  
Rationale  
Evidence used  
Actor  
Timestamp  
---

### **50\. Verification tasks**

Make them persistent objects.

---

### **51\. Cross-district handoff**

Support coordination.

---

### **52\. Case comparison**

Compare:

Entities  
Network  
Timeline  
Communications  
Transactions  
Evidence  
Geography  
---

# **P1 — COPILOT**

### **53\. Remove guilt prompt**

Delete:

> Is the accused guilty...?

---

### **54\. Better quick prompts**

Use:

What evidence connects these cases?  
What changed since the previous snapshot?  
What evidence is missing?  
Which entity links these investigations?  
Summarize only verified evidence.  
Explain the financial path with citations.  
---

### **55\. Context-bound Copilot**

Show:

Current case  
Current snapshot  
Evidence scope  
Network scope  
---

### **56\. Claim classification**

Copilot output should distinguish:

OBSERVED  
INFERRED  
MISSING  
VERIFIED  
---

### **57\. Citation-first answers**

Every substantive claim should resolve to:

source  
record  
timestamp  
---

# **P1 — AUDIT / SECURITY**

### **58\. Audit table redesign**

Show:

Time  
Actor  
Action  
Target  
Integrity

Click to expand context.

---

### **59\. Hide raw event names**

Show human text instead of:

copilot\_answered  
timeline\_viewed  
---

### **60\. Fix Audit overflow**

The current rightmost audit metadata column visually overflows.

---

### **61\. Real anchor verification**

Click:

> Verify

and actually recompute/validate the anchor.

---

### **62\. Do not overclaim blockchain**

Only call it permissioned blockchain if an actual permissioned blockchain exists.

Otherwise:

> Tamper-Evident Audit Ledger

---

### **63\. Mask sensitive fields**

Phone/vehicle/address/national ID should be masked where appropriate.

---

# **P1 — TIMELINE**

### **64\. Separate event types**

Investigative  
Source  
System  
Evidence  
Resolution  
Decision  
---

### **65\. Show event provenance**

Each event:

Observed  
Ingested  
Processed  
Source  
Actor  
---

### **66\. Investigation change mode**

Add:

> Investigative Changes

---

# **P1 — PERFORMANCE**

### **67\. Measure before optimization**

Capture:

request count  
request waterfall  
API latency  
Neo4j latency  
Postgres latency  
frontend transformation  
render time  
---

### **68\. TanStack Query**

Use:

stable query keys  
staleTime  
cache reuse  
deduplication  
cancellation  
prefetch  
---

### **69\. Backend profiling**

Inspect:

N+1  
unbounded graph traversal  
repeated graph calculations  
huge responses  
serial requests  
---

### **70\. Graph performance**

Use:

progressive expansion  
cluster collapse  
node type filtering  
1-hop default  
2-hop on request  
---

# **TEAM SPLIT**

Now the important part: **split this cleanly so the two teammates can work in parallel without stepping on each other.**

---

# **TEAMMATE 1 — INTELLIGENCE \+ BACKEND \+ DOMAIN \+ DATA WORKFLOW**

## **Mission**

Own everything that determines **what NEXUS calculates, how it interprets evidence, how state changes propagate, and whether the backend behaves like a real investigation system.**

Do not spend time polishing unrelated frontend layouts.

---

## **A1. Fix document ingestion**

Own:

/api/v1/documents

Fix:

404  
upload  
ingestion  
source validation  
case association  
persistence

Acceptance:

PDF selected  
↓  
source validated  
↓  
upload succeeds  
↓  
ingestion begins  
↓  
source record created  
↓  
evidence available  
↓  
graph/evidence references work  
---

## **A2. Canonical identifiers**

Define canonical models for:

Investigation  
FIR  
Entity  
Evidence  
Pulse  
Lead  
VerificationTask  
Snapshot  
AuditEvent

Create one resolver path for each.

---

## **A3. Intelligence Event model**

Create the root object:

IntelligenceEvent

It should connect:

NetworkDiff  
EvidenceAssessment  
Pulse  
AffectedCases  
VerificationTask  
Decision  
AuditEvent  
---

## **A4. Network Diff**

Ensure the backend can return:

added nodes  
removed nodes  
added edges  
removed edges  
changed identifiers  
new bridges  
changed routes

between two snapshots.

---

## **A5. Evidence Assessment**

Standardize:

SUPPORTS  
CONFLICTS  
MISSING  
INFERRED  
VERIFIED

Make assessment explainable.

---

## **A6. Abstention**

Implement explicit:

ABSTAIN

with:

reason  
missing evidence  
required corroboration

No forced positive signal.

---

## **A7. Next Best Verification**

Create persistent verification tasks:

created  
assigned  
requested  
received  
reviewed  
verified  
dismissed  
---

## **A8. Closed-loop propagation**

Implement:

investigator decision  
→ graph state change  
→ snapshot  
→ NetworkDiff  
→ signal refresh

This is a P0 task.

---

## **A9. Entity Resolution**

Improve backend resolution semantics:

candidate  
match  
ambiguous  
non-match  
confirmed

Do not use one opaque score as the decision.

---

## **A10. Entity Search**

Fix broad name matching.

A name token alone must not create:

> MATCHED 85%

Return:

candidate

until corroborated.

---

## **A11. Entity Fusion evidence model**

Return actual:

supporting factors  
conflicting factors  
unknown factors  
---

## **A12. Network Adaptation**

Formalize:

previous relationship  
new relationship  
replacement conduit  
supporting evidence  
---

## **A13. Case DNA / Similar Cases**

Ensure dimensions and similarities are real and explainable.

No decorative scores.

---

## **A14. Affected investigation routing**

For each signal:

affected case  
owner  
district  
reason  
---

## **A15. Timeline backend**

Separate:

observed  
ingested  
processed  
investigator action  
---

## **A16. Audit integrity**

Ensure:

event  
hash  
previous hash  
anchor  
verification

actually work.

---

## **A17. Legal/domain corrections**

Audit all backend-generated text for:

* outdated CrPC references  
* unsupported legal claims  
* "guilt"  
* "offender"  
* "syndicate"  
* "risk"  
* "forecast"

Current BNSS Section 94 concerns production of documents/electronic communications, so current legal references should be checked against the official text before being surfaced. ([India Code](https://www.indiacode.nic.in/bitstream/123456789/21180/1/bharatiya_nagarik_suraksha_sanhita%2C_2023_1723877824_66c049c04ad7c_%281%29.pdf?utm_source=chatgpt.com))

---

## **A18. Backend performance**

Profile:

PostgreSQL  
Neo4j  
API waterfalls  
large graph queries  
N+1  
repeated analytics

Provide optimized endpoints where necessary.

---

## **A19. Test suite**

Add tests for:

document ingestion  
canonical IDs  
entity ambiguity  
abstention  
verification lifecycle  
network diff  
signal propagation  
timeline provenance  
audit verification  
---

## **TEAMMATE 1 SHOULD NOT DO**

sidebar redesign  
colors  
typography  
component spacing  
modal styling  
navigation polish  
graph visual layout  
Copilot visual design

Those belong to Teammate 2\.

---

# **TEAMMATE 2 — FRONTEND \+ UX \+ INVESTIGATION WORKSPACE \+ PERFORMANCE**

## **Mission**

Own everything the investigator **sees, clicks, understands and navigates through.**

---

## **B1. Sidebar**

Final:

INTELLIGENCE  
Intelligence Center  
Lead Inbox  
Investigation Worklist

INVESTIGATION  
Network Explorer  
Entity Search  
Entity Fusion  
Timeline & Events  
Evidence & Provenance

ASSIST  
Investigator Copilot

GOVERNANCE  
Audit & Integrity  
---

## **B2. Intelligence Center**

Default:

Network Pulse

Top viewport:

Active Pulses  
Evidence Status  
Affected Investigations  
Network Changes  
---

## **B3. Pulse UI**

Show:

what changed  
why appeared  
evidence  
uncertainty  
early warning  
verification  
---

## **B4. Evidence UI**

Use:

Supports  
Conflicts  
Missing  
Inferred  
Verified  
---

## **B5. Abstention UI**

Make:

ABSTAINED

as visually important as a successful detection.

---

## **B6. Next Best Verification UI**

Show:

Objective  
Target  
Why  
Missing evidence  
Owner  
Status  
---

## **B7. Investigation Workspace**

Build:

Investigation Overview  
Network  
Timeline  
Similar Cases  
Evidence  
Verification  
Copilot  
Audit  
---

## **B8. Case Graph**

Default:

Case Only  
1 Hop  
2 Hops  
3 Hops

No overwhelming global graph on first entry.

---

## **B9. "Why is this shown?"**

Add to entity/node inspector.

---

## **B10. Edge Inspector**

Click edge → evidence details.

---

## **B11. Entity Fusion UI**

Primary:

support  
conflict  
unverified

Secondary:

technical similarity score  
---

## **B12. Entity Search UI**

Replace:

> Matched 85%

with:

> Candidate — name match only

when appropriate.

---

## **B13. Network Transformation UI**

Make:

BEFORE  
→  
DECISION  
→  
AFTER

highly visual.

---

## **B14. Timeline UI**

Add:

All  
Investigative Changes  
FIR  
Evidence  
CDR  
Transactions  
Entity Resolution  
---

## **B15. Similar Cases UI**

Improve empty state.

Show:

searched N cases  
threshold  
closest case  
why not matched  
---

## **B16. Case DNA UI**

Replace technical wording:

> Harmonic vector average

with investigator-readable dimensions.

---

## **B17. Copilot UI**

Remove:

> Is accused guilty?

Add grounded investigator prompts.

Add current investigation context.

---

## **B18. Audit UI**

Remove:

audit\_batch\_anchored  
copilot\_answered  
timeline\_viewed

from primary display.

Create expandable event details.

Fix overflow.

---

## **B19. Evidence drawer**

Fix:

legacy hash  
canonical source  
source ID resolver

presentation.

---

## **B20. Sensitive-field UI**

Mask:

phone  
vehicle  
national ID  
address

where appropriate.

---

## **B21. Loading states**

Never display false:

(0)

while loading.

Never show:

null  
undefined  
---

## **B22. TanStack Query**

Use:

staleTime  
cache  
dedupe  
prefetch  
cancel  
---

## **B23. Graph rendering performance**

Implement:

progressive rendering  
node filtering  
edge filtering  
cluster collapse  
virtualized/optimized graph where applicable  
---

## **B24. Global UI consistency**

Standardize:

status labels  
badges  
buttons  
empty states  
error states  
drawers  
modals  
metrics  
timestamps  
---

# **TEAMMATE 2 SHOULD NOT DO**

Do not redesign:

backend schemas  
Neo4j algorithms  
entity-resolution formulas  
NetworkDiff logic  
evidence scoring logic  
audit hashing  
ingestion pipeline

unless an explicit frontend/backend contract requires a small change.

---

# **COORDINATION CONTRACT BETWEEN TEAMMATES**

This part is important.

Before coding, both teammates agree on these objects:

IntelligenceEvent  
NetworkDiff  
EvidenceAssessment  
VerificationTask  
Investigation  
EntityResolutionResult  
TimelineEvent

Teammate 1 owns their **data shape and behavior**.

Teammate 2 owns their **presentation and interaction**.

Neither creates a parallel version.

---

# **SHARED UX LANGUAGE**

Both teammates must use exactly these terms.

## **Intelligence**

Network Pulse  
Network Change  
Operational Early Warning  
Verification Required

## **Evidence**

SUPPORTS  
CONFLICTS  
MISSING  
INFERRED  
VERIFIED

## **Entity resolution**

CANDIDATE  
MATCH  
AMBIGUOUS  
UNRESOLVED  
NON-MATCH  
CONFIRMED

## **Signal lifecycle**

NEW  
REVIEWING  
VERIFICATION REQUIRED  
CONFIRMED  
DISMISSED  
STALE  
---

# **FINAL SIH DEMO FLOW**

Both teammates should optimize their work toward this exact walkthrough.

## **1\. Login**

Investigator lands directly in:

**Intelligence Center**

---

## **2\. Network Pulse**

Judge sees:

> New cross-investigation network bridge

---

## **3\. Why did it appear?**

Show:

\+3 edges  
\+1 bridge  
2 investigations affected  
---

## **4\. Evidence**

Show:

2 supporting  
1 missing  
0 conflicts  
---

## **5\. Abstention**

Demonstrate:

> NEXUS does not treat unresolved subscriber identity as established fact.

---

## **6\. Verification**

Create:

> Verify subscriber identity

---

## **7\. Investigation Workspace**

Open affected FIR.

---

## **8\. Before/After Network**

Show:

before  
vs  
after  
---

## **9\. Entity Resolution**

Show:

supporting facts  
conflicts  
unknown  
---

## **10\. Investigator decision**

Confirm / reject / defer.

---

## **11\. Network Transformation Delta**

Show:

entities merged  
edges rewired  
cross-case bridge formed  
---

## **12\. Timeline**

Show:

original FIR  
evidence  
communications  
resolution  
network change  
investigator decision  
---

## **13\. Copilot**

Ask:

> "Summarize only the verified connections between these investigations."

Answer must contain evidence references.

---

## **14\. Evidence Dossier**

Generate structured dossier.

---

## **15\. Audit**

Show:

who  
did what  
when  
on what evidence  
hash  
integrity  
---

# **THE THREE DEMO MOMENTS I WOULD PRIORITIZE ABOVE EVERYTHING ELSE**

### **DEMO MOMENT 1 — NETWORK CHANGE**

Show:

Yesterday:  
two separate investigation components.

Today:  
new relationship connects them.

NEXUS detected the structural change.

### **DEMO MOMENT 2 — ABSTENTION \+ VERIFICATION**

Show:

NEXUS sees a possible link,  
but refuses to treat it as confirmed  
because independent identity evidence is missing.

It then tells the investigator exactly what to verify.

This is one of the strongest ideas in the entire project.

### **DEMO MOMENT 3 — CLOSED LOOP**

Show:

Investigator confirms evidence  
↓  
entity resolution changes  
↓  
graph changes  
↓  
cross-case bridge becomes visible  
↓  
affected investigation updated  
↓  
action appears in audit

That is the part that can make NEXUS feel substantially more mature than a collection of graph analytics.

---

# **FINAL "DO NOT BUILD" LIST**

Both teammates must avoid adding:

generic AI chatbot features  
generic crime prediction  
suspect risk scores  
guilt prediction  
dangerousness scores  
more generic graph metrics  
more dashboards  
more unnecessary tabs  
black-box confidence numbers  
fake live data  
fake blockchain  
fake legal certifications  
fake real-time claims  
---

# **FINAL ACCEPTANCE CRITERIA**

The work is complete only when:

\[ \] Document ingestion works on deployed backend  
\[ \] Invalid document/source combinations are handled  
\[ \] /intelligence is default  
\[ \] Network Pulse is default Intelligence view  
\[ \] One investigation can be followed end-to-end  
\[ \] Network Diff is visible  
\[ \] Evidence assessment is explainable  
\[ \] Abstention works  
\[ \] Verification tasks are persistent  
\[ \] Investigator decision changes system state  
\[ \] Graph updates after verified decision  
\[ \] Entity resolution explains support/conflict  
\[ \] Entity Search doesn't overclaim matches  
\[ \] Similar Cases explains both matches and non-matches  
\[ \] Timeline distinguishes event types  
\[ \] Edge provenance is inspectable  
\[ \] Copilot is context-bound  
\[ \] Guilt prompt removed  
\[ \] Audit is understandable  
\[ \] Audit integrity verification works  
\[ \] Legal terminology is current and appropriately scoped  
\[ \] Sensitive identifiers are protected  
\[ \] No raw null/undefined/developer strings visible  
\[ \] No P1/P2 labels visible  
\[ \] No unsupported "syndicate/offender/risk" claims  
\[ \] Synthetic/NCRB-calibrated data is clearly identified  
\[ \] Duplicate signals are consolidated  
\[ \] Affected investigations are routed correctly  
\[ \] Performance is measured before/after  
\[ \] Existing tests remain green  
\[ \] Production build passes

## **Final product positioning**

Do not end the SIH demo with:

> "NEXUS uses AI, Neo4j and graph algorithms to analyze criminal networks."

End it with the actual operational value:

> **"NEXUS continuously compares investigation network states, identifies meaningful structural changes, traces every signal back to evidence, abstains when corroboration is insufficient, and converts the uncertainty into a concrete verification action for the investigator."**

That is the product the UI should make the judges experience—not merely hear about.

The government context also makes this positioning more credible: ICJS is explicitly intended to integrate criminal-justice data sources and support analytics/AI in investigations, while MHA already lists criminal-network link analysis as an ICJS capability. ([Ministry of Home Affairs](https://www.mha.gov.in/en/commoncontent/icjsncrb-administration?utm_source=chatgpt.com))

So your differentiation should be **the intelligence workflow on top of interconnected records**, especially the evidence-aware **change → abstain → verify → update** loop, rather than claiming to replace ICJS or merely duplicating graph link analysis.
