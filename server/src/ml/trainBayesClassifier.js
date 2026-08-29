const classifier =
  require("./bayesClassifier");

// Positive examples
const POSITIVE_EXAMPLES = [
  "company profit rises strongly",
  "shares gain after strong earnings",
  "revenue increases and outlook remains stable",
  "stock market closes higher",
  "company reports record profit",
  "earnings rise significantly",
  "share price increases after strong results",
  "business expansion boosts revenue",
  "company profit jumps sharply",
  "quarterly earnings beat expectations",
  "revenue grows year on year",
  "company reports higher net income",
  "stocks rise as investor confidence improves",
  "market gains on strong corporate earnings",
  "aspi closes higher",
  "shares advance during trading",
  "foreign investors increase purchases",
  "foreign investment rises",
  "company receives rating upgrade",
  "credit rating outlook improves",
  "rating affirmed with stable outlook",
  "company expands operations",
  "new investment supports future growth",
  "tourism arrivals increase strongly",
  "tourism revenue grows",
  "exports rise during the quarter",
  "economic growth accelerates",
  "business confidence improves",
  "company announces profitable expansion",
  "bank reports higher quarterly profit",
  "loan growth supports bank earnings",
  "company secures major new contract",
  "firm wins valuable project",
  "company launches successful new product",
  "market rebounds after previous losses",
  "stocks recover strongly",
  "company reduces operating costs and increases profit",
  "strong demand boosts sales",
  "sales increase significantly",
  "company reports strong financial performance",
  "dividend increased after strong profit",
  "cash flow improves",
  "company enters new growth market",
  "export earnings increase",
  "investment inflows strengthen",
  "shareholders benefit from higher earnings",
  "company exceeds revenue expectations",
  "profit margin improves",
  "bank maintains strong capital position",
  "company successfully completes expansion project",
  "foreign investors buy",
"foreign investors increase purchases",
"foreign inflows rise",
"foreign investment inflows",
"rating affirmed",
  "ratings affirmed",
  "outlook stable",
  "stable outlook",
  "affirms rating",
  "credit rating affirmed",
  "strong demand for treasury bills",
"treasury bill auction oversubscribed",
"foreign investors buy treasury bills"
];

// Negative examples
const NEGATIVE_EXAMPLES = [
  "company reports heavy losses",
  "stock market closes lower",
  "revenue falls sharply",
  "inflation rises and economic risks increase",
  "shares drop after weak earnings",
  "stock market declines",
  "company profit falls",
  "economic uncertainty increases",
  "stocks close down",
  "aspi drops during trading",
  "market falls on investor concerns",
  "company reports lower profit",
  "quarterly earnings miss expectations",
  "revenue declines year on year",
  "company records a net loss",
  "shares fall after disappointing results",
  "company receives credit downgrade",
  "rating outlook turns negative",
  "debt levels increase sharply",
  "borrowing costs rise",
  "inflation reaches a new high",
  "consumer prices increase rapidly",
  "tourism revenue declines",
  "exports fall during the quarter",
  "foreign investment decreases",
  "investor confidence weakens",
  "economic growth slows",
  "company cuts production due to weak demand",
  "sales decline significantly",
  "company faces liquidity problems",
  "bank reports rising bad loans",
  "loan defaults increase",
  "company loses major contract",
  "operating costs increase sharply",
  "profit margin declines",
  "market volatility increases",
  "shares plunge after poor results",
  "company warns of weaker earnings",
  "cash flow deteriorates",
  "company delays major investment",
  "business confidence falls",
  "stocks trend lower",
  "market closes down on global jitters",
  "company reports declining revenue and profit",
  "currency weakness increases costs",
  "fuel prices rise sharply",
  "interest rates rise and pressure borrowing",
  "company cuts dividend",
  "company faces regulatory penalties",
  "financial performance weakens"
];

// Neutral examples
const NEUTRAL_EXAMPLES = [
  "company announces annual general meeting",
  "board appoints new director",
  "company releases quarterly report",
  "shareholders approve scheduled meeting",
  "company signs administrative agreement",
  "company publishes financial statement",
  "board meeting scheduled for next month",
  "company announces management changes",
  "stock market closes flat",
  "stocks remain unchanged",
  "aspi ends mostly unchanged",
  "market trades flat",
  "share price remains stable",
  "company signs partnership agreement",
  "company enters memorandum of understanding",
  "company announces new board member",
  "company changes registered office",
  "company publishes annual report",
  "company announces dividend payment date",
  "company schedules investor meeting",
  "board approves routine resolution",
  "company holds shareholder meeting",
  "company releases corporate disclosure",
  "firm announces internal restructuring",
  "company appoints new chief executive",
  "company changes company secretary",
  "company announces acquisition discussions",
  "business council signs cooperation agreement",
  "company enters preliminary agreement",
  "company announces planned investment",
  "company submits regulatory filing",
  "company issues market announcement",
  "bank announces new loan product",
  "company launches new service",
  "firm opens new branch",
  "company signs distribution agreement",
  "company enters strategic partnership",
  "government announces economic policy proposal",
  "central bank publishes monetary policy report",
  "company reports unchanged revenue",
  "earnings remain broadly stable",
  "profit remains unchanged from previous year",
  "market turnover remains steady",
  "company maintains existing credit rating",
  "rating remains unchanged",
  "company announces routine maintenance",
  "company updates corporate strategy",
  "company completes administrative transaction",
  "shareholders approve board proposal",
  "company announces upcoming product launch",
  "treasury bill auction completed",
"government sells treasury bills",
"central bank treasury bill auction",
"treasury bills issued",
"government raises funds through treasury bills"
];

// Add positive training documents
for (const text of POSITIVE_EXAMPLES) {
  classifier.addDocument(
    text,
    "positive"
  );
}

// Add negative training documents
for (const text of NEGATIVE_EXAMPLES) {
  classifier.addDocument(
    text,
    "negative"
  );
}

// Add neutral training documents
for (const text of NEUTRAL_EXAMPLES) {
  classifier.addDocument(
    text,
    "neutral"
  );
}

// Train after all documents are added
classifier.train();

module.exports = classifier;