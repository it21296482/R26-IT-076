import { useEffect, useMemo, useState } from "react";
import SiteHeader from "../../components/SiteHeader";
import { useAuth } from "../../hooks/useAuth";
import api from "../../lib/api";
import axios from "axios";
import {
    Sparkles,
    TrendingUp,
    Brain,
    Globe2,
    AlertTriangle
} from "lucide-react";


const initialRecordForm = {
    stock: "",
    close: "",
    volume: "",
    ma10: "",
    ma50: "",
    volatility: "",
};

const USERS_PER_PAGE = 5;
const RECORDS_PER_PAGE = 6;

const buildTemplateFile = () => {
    const template = [
        "tradeDate,open,high,low,close,adjustedClose,volume",
        "2026-01-02,182.50,185.00,181.25,184.40,184.40,1450000",
        "2026-01-03,184.40,186.00,183.90,185.55,185.55,1582300",
    ].join("\n");

    const blob = new Blob([template], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "historical-price-template.csv";
    anchor.click();
    URL.revokeObjectURL(url);
};

function RiskDashboard() {
    const { user: currentUser } = useAuth();
    const [recordForm, setRecordForm] = useState(initialRecordForm);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [marketData, setMarketData] = useState({
        gold: 0,
        oil: 0,
    });
    const [loadingMarket, setLoadingMarket] = useState(true);
    const [result, setResult] = useState(null);
    const [m10, setM10] = useState('');
    const [m50, setM50] = useState('');
    const [Close, setClose] = useState('')
    const [Volume, setVolume] = useState('')
    const [volatility, setvolatility] = useState('')
    const [secName, setsecName] = useState('')
    const [loading, setLoading] = useState(false)
    const [showAI, setShowAI] = useState(true);
    const [buttonLoading,setButtonLoding] = useState(false);

    useEffect(() => {

        const fetchMarketData = async () => {

            try {
                setLoadingMarket(true);

                const res = await axios.get("http://localhost:5000/market-data");

                setMarketData({
                    gold: res.data.gold.price,
                    oil: res.data.oil.price,
                });

            } catch (err) {
                console.error("Market data error:", err);

            } finally {
                setLoadingMarket(false);
            }
        };

        fetchMarketData();

    }, []);


    const stats = [
        ["GOLD", loadingMarket ? "Loading..." : `$ ${Number(marketData.gold).toFixed(2)}`],
        ["CRUDE", loadingMarket ? "Loading..." : `$ ${Number(marketData.oil).toFixed(2)}`]
    ];

    const getData = (v) => {
        console.log(v);

        setLoading(true);
        setsecName(v)

        let symbol = "";

        if (v === "HEMAS HOLDINGS PLC") {
            symbol = "HHL.N0000";
        } else if (v === "JOHN KEELLS HOLDINGS PLC") {
            symbol = "JKH.N0000";
        } else if (v === "CHEVRON LUBRICANTS LANKA PLC") {
            symbol = "LLUB.N0000";
        }

        console.log("Symbol:", symbol);

        axios.get(`http://localhost:5000/ma10/${symbol}`)
            .then((res) => {
                setM10(res.data.ma10);
            })
            .catch((err) => {
                console.error(err);
            });

        axios.get(`http://localhost:5000/ma50/${symbol}`)
            .then((res) => {
                setM50(res.data.ma50);
            })
            .catch((err) => {
                console.error(err);
            });

        axios.get(`http://localhost:5000/volatility/${symbol}`)
            .then((res) => {
                setvolatility(res.data.volatility);
            })
            .catch((err) => {
                console.error(err);
            });

        axios.get('http://localhost:5000/cse-filter')
            .then((res) => {

                const stockData = res.data.data.find(
                    item => item["Company Name"] === v
                );

                if (stockData) {

                    const close = stockData["**Last Trade (Rs.)"];
                    setClose(stockData["**Last Trade (Rs.)"]);
                    setVolume(stockData["Share Volume"]);
                    const volume = stockData["Share Volume"];
                    console.log("Close:", close);
                    console.log("Volume:", volume);

                    // save to state if needed
                    setRecordForm(prev => ({
                        ...prev,
                        close,
                        volume
                    }));

                } else {

                    console.log("Company not found");

                }

            })
            .catch((err) => {
                console.log(err);
            });

        setLoading(false);

    };

    const handleEditRecord = (record) => {
        setRecordForm({
            stock: record.stock || "",
            close: record.close || "",
            volume: record.volume || "",
            ma10: record.ma10 || "",
            ma50: record.ma50 || "",
            volatility: record.volatility || ""
        });

        setError("");
        setSuccess("");
    };
    const handlePredict = async (e) => {
        e.preventDefault();
        setButtonLoding(true)

        let symbol = "";

        if (secName === "HEMAS HOLDINGS PLC") {
            symbol = "HHL";
        } else if (secName === "JOHN KEELLS HOLDINGS PLC") {
            symbol = "JKH";
        } else if (secName === "CHEVRON LUBRICANTS LANKA PLC") {
            symbol = "LLUB";
        }

        const ob = {
            stock: symbol || "",
            close: Close || 0,
            volume: Volume || 0,
            ma10: m10 || 0,
            ma50: m50 || 0,
            volatility: volatility || 0
        }

        console.log(ob)

        try {
            const res = await axios.post("http://localhost:5000/predict_auto", ob);
            console.log(res.data)
            setResult(res.data);

        } catch (err) {
            console.error(err);
        }

        setButtonLoding(false)
    };

    console.log(m10, m50, Close, Volume)

    return (
        <div className="page-with-sticky-header min-h-screen pb-16">
            <SiteHeader compact />

            <main className="shell space-y-10">
                <section className="grid gap-8 lg:grid-cols-[1fr_360px]">
                    <div className="space-y-5 fade-rise">
                        <p className="eyebrow">Risk Engine Tool</p>
                        <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">Predict before you invest.</h1>
                        <p className="max-w-3xl text-lg leading-8 text-slate-600">
                            Analyze potential risks and investment impact using global market factors, trends, and data-driven insights to make smarter financial decisions.
                        </p>
                    </div>

                    <div className="market-hero relative overflow-hidden p-6 fade-rise-delay-1">
                        <div className="market-orb absolute -right-16 top-4 h-40 w-40 opacity-70" />
                        <div className="relative z-10 grid gap-4">
                            {stats.map(([label, value]) => (
                                <div className="rounded-2xl border border-white/10 bg-white/8 px-4 py-4" key={label}>
                                    <p className="text-xs uppercase tracking-[0.22em] text-blue-100/75">{label}</p>
                                    <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>


                <section className="grid gap-8 2xl:grid-cols-[0.86fr_1.14fr]">
                    <article className="surface-panel fade-rise">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                                <p className="eyebrow !text-slate-500">Risk prediction</p>

                                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                                    Add Market Data
                                </h2>

                                <p className="mt-3 max-w-xl text-sm leading-7 text-slate-600">
                                    Enter stock indicators and external market factors for ML-based risk
                                    prediction and forecasting.
                                </p>
                            </div>
                        </div>

                        <form onSubmit={handlePredict} className="mt-8 space-y-6">

                            {/* COMPANY SELECT */}
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-slate-700">
                                    Stock Company
                                </label>

                                <select
                                    className="input-surface w-full"
                                    value={recordForm.stock}
                                    onChange={(e) => getData(e.target.value)}
                                >
                                    <option value="">
                                        Select Company
                                    </option>

                                    <option value="HEMAS HOLDINGS PLC">
                                        HEMAS HOLDINGS PLC
                                    </option>

                                    <option value="JOHN KEELLS HOLDINGS PLC">
                                        JOHN KEELLS HOLDINGS PLC
                                    </option>

                                    <option value="CHEVRON LUBRICANTS LANKA PLC">
                                        CHEVRON LUBRICANTS LANKA PLC
                                    </option>

                                </select>
                            </div>


                            {/* LOADING */}
                            {loading && (
                                <div className="flex items-center gap-3 rounded-lg bg-blue-50 p-4 text-blue-700">

                                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>

                                    <span>
                                        Fetching latest stock data...
                                    </span>

                                </div>
                            )}



                            {/* DATA DISPLAY */}
                            <div className="grid gap-5 md:grid-cols-2">


                                <InputCard
                                    title="Close Price"
                                    value={Close}
                                />


                                <InputCard
                                    title="Volume"
                                    value={Volume}
                                />


                                <InputCard
                                    title="MA 10"
                                    value={m10}
                                />


                                <InputCard
                                    title="MA 50"
                                    value={m50}
                                />


                                <InputCard
                                    title="Volatility"
                                    value={volatility}
                                />


                            </div>



                            <button
                                className="primary-cta w-full disabled:opacity-50"
                                type="submit"
                                disabled={loading || !Close || buttonLoading}
                                
                            >

                                {buttonLoading ? "Loading..." : "Submit"}

                            </button>


                        </form>

                        {result && (
                            <div className="">

                                {/* HEADER */}
                                <div className="mt-10 rounded-3xl overflow-hidden bg-white border border-slate-200 shadow-2xl">

                                    <div className="p-6 bg-gradient-to-br from-slate-900 via-indigo-900 to-blue-900 text-white">

                                        <div className="flex items-center justify-between">

                                            <div className="flex items-center gap-4">
                                                <div className="h-14 w-14 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center text-3xl">📊</div>
                                                <div>
                                                    <h3 className="text-2xl font-bold">Risk Analysis</h3>
                                                    <p className="text-sm text-blue-200">AI powered market prediction </p>
                                                </div>
                                            </div>

                                            <span className={`px-5 py-2 rounded-full text-sm font-bold shadow-lg
                                            ${result.risk === "HIGH" ?
                                                    "bg-red-500" :
                                                    result.risk === "MEDIUM"
                                                        ?
                                                        "bg-yellow-400"
                                                        :
                                                        "bg-green-500"
                                                }`}>{result.risk} RISK </span>
                                        </div>
                                    </div>

                                    <div className="p-6 space-y-8">
                                        <div className="grid md:grid-cols-2 gap-5">
                                            <div className="rounded-2xl p-5 bg-gradient-to-br from-blue-50 to-white border border-blue-100">
                                                <p className="text-xs uppercase tracking-widest text-slate-500"> Selected Stock </p>
                                                <div className="mt-3 flex justify-between items-center">
                                                    <h2 className="text-3xl font-bold text-slate-900">{result.stock}</h2>
                                                    <span className="text-3xl"> 📈</span>
                                                </div>
                                            </div>

                                            <div className="rounded-2xl p-5 bg-gradient-to-br from-green-50 to-white border border-green-100">
                                                <p className="text-xs uppercase tracking-widest text-slate-500"> Prediction Confidence </p>
                                                <div className="mt-3 flex justify-between items-center">
                                                    <h2 className="text-3xl font-bold text-green-700">
                                                        {
                                                            result.risk === "HIGH" ?
                                                                "78%" :
                                                                result.risk === "MEDIUM" ?
                                                                    "65%" : "82%"
                                                        }
                                                    </h2>
                                                    <span className="text-3xl">🎯</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div>
                                            <div className="flex items-center justify-between mb-5">
                                                <h4 className="text-xl font-bold text-slate-800"> 📌 Key Market Influencers </h4>
                                                <span className="text-xs bg-slate-100 px-3 py-1 rounded-full text-slate-500">AI Factors</span>
                                            </div>

                                            <div className="space-y-4">
                                                {result.top_factors.map((f, i) => (
                                                    <div key={i} className="group rounded-2xl border bg-gradient-to-r from-white to-slate-50 p-5 hover:shadow-xl transition">
                                                        <div className="flex justify-between items-center">
                                                            <div>
                                                                <p className="font-bold text-slate-800 text-lg"> {f.factor} </p>
                                                                <p className="text-xs text-slate-500">Influence on risk prediction </p>
                                                            </div>

                                                            <span className={`px-4 py-2 rounded-full text-xs font-bold
                                                                    ${f.impact > 0 ?
                                                                    "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
                                                                {f.impact > 0 ? "+" : ""}
                                                                {Number(f.impact).toFixed(4)}
                                                            </span>
                                                        </div>
                                                        <div className="mt-5 h-3 rounded-full bg-slate-100 overflow-hidden">
                                                            <div
                                                                className={`h-full rounded-full transition-all duration-700
                                                                    ${f.impact > 0 ?
                                                                        "bg-gradient-to-r from-red-400 to-orange-500"
                                                                        :
                                                                        "bg-gradient-to-r from-emerald-400 to-green-500"
                                                                    } `}

                                                                style={{
                                                                    width:
                                                                        `${Math.min(
                                                                            Math.abs(f.impact) * 250,
                                                                            100
                                                                        )}%`
                                                                }}

                                                            />

                                                        </div>
                                                    </div>
                                                ))
                                                }
                                            </div>
                                        </div>

                                        <div className="rounded-2xl bg-gradient-to-r from-indigo-50 to-blue-50 p-5 border border-indigo-100">
                                            <p className="text-sm text-slate-600 leading-7">
                                                💡 The prediction combines historical price movements,
                                                technical indicators, and global market conditions
                                                to estimate potential risk levels.
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* MARKET DATA CARDS */}

                                <div className="grid md:grid-cols-3 gap-4 mt-6">

                                    <MarketCard
                                        title="Gold"
                                        value={`$${Number(result.market_data.gold).toFixed(2)}`}
                                        icon="🥇"
                                    />

                                    <MarketCard
                                        title="Oil"
                                        value={`$${Number(result.market_data.oil).toFixed(2)}`}
                                        icon="🛢️"
                                    />

                                    <MarketCard
                                        title="VIX"
                                        value={Number(result.market_data.vix).toFixed(2)}
                                        icon="📉"
                                    />

                                </div>

                                <div className="mt-8 rounded-3xl overflow-hidden border border-indigo-200 shadow-xl">
                                    <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-6 text-white">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="bg-white/20 p-3 rounded-2xl">
                                                    <Sparkles size={28} />
                                                </div>

                                                <div>
                                                    <h3 className="text-2xl font-bold">AI Market Analyst </h3>
                                                    <p className="text-sm text-white/80"> AI generated explanation</p>
                                                </div>

                                            </div>

                                            <Brain size={35} />

                                        </div>

                                    </div>

                                    <div className="bg-white p-6">
                                        <div className="rounded-2xl bg-gradient-to-br from-indigo-50 to-white p-5 leading-8 text-slate-700">
                                            <p className="whitespace-pre-line text-[15px]">{result.ai_explanation}</p>
                                        </div>

                                        <div className="mt-5 flex gap-3 items-center rounded-xl bg-yellow-50 border border-yellow-200 p-4 text-sm text-yellow-800">
                                            <AlertTriangle size={20} />
                                            This AI analysis is for informational purposes only,
                                            not financial advice.
                                        </div>

                                    </div>

                                </div>
                            </div>
                        )}
                    </article>
                </section>
            </main>
        </div>
    );
}

export default RiskDashboard;


const InputCard = ({ title, value }) => {

    return (

        <div className="
            rounded-xl
            border
            border-slate-200
            bg-white
            p-4
            shadow-sm
        ">

            <p className="text-sm text-slate-500">
                {title}
            </p>


            <div className="
                mt-2
                flex
                items-center
                justify-between
            ">

                <span className="
                    text-xl
                    font-bold
                    text-slate-800
                ">

                    {value || "--"}

                </span>


                <span className="
                    rounded-full
                    bg-green-100
                    px-3
                    py-1
                    text-xs
                    text-green-700
                ">

                    Auto

                </span>

            </div>

        </div>

    )
}



const MarketCard = ({ title, value, icon }) => {

    return (

        <div className="
            rounded-2xl
            bg-white
            border
            p-5
            shadow-sm
            hover:shadow-lg
            transition
        ">

            <div className="
                flex
                items-center
                justify-between
            ">

                <span className="text-3xl">
                    {icon}
                </span>


                <Globe2
                    size={20}
                    className="text-slate-400"
                />

            </div>



            <p className="
                mt-3
                text-sm
                text-slate-500
            ">

                {title}

            </p>



            <p className="
                text-2xl
                font-bold
                text-slate-800
            ">

                {value}

            </p>


        </div>

    )
}