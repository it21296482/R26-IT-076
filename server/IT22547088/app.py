from flask import Flask, request, jsonify
import joblib
import numpy as np
import pandas as pd
import shap
import yfinance as yf
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import glob
import re
from pymongo import MongoClient
from datetime import datetime
from ai_recommender import StockAIExplainer  # Import your recommender class
import traceback

app = Flask(__name__)
CORS(app)
# ============================================
# LOAD MODEL + ENCODER
# ============================================

model = joblib.load("risk_model.pkl")
encoder = joblib.load("stock_encoder.pkl")

MONGO_URI = "mongodb+srv://sajindu:saji1234@cluster0.bx77a.mongodb.net/stock_market"

client = MongoClient(MONGO_URI)

db = client["CSE_DATABASE"]

stock_collection = db["daily_stock_prices"]

features = [
    "Close",
    "Volume",
    "MA10",
    "MA50",
    "Volatility",
    "Gold",
    "Oil",
    "VIX",
    "Stock_encoded"
]

risk_map = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}

explainer = shap.TreeExplainer(model)

# ============================================
# MAIN API
# ============================================

def clear_old_files(folder):
    files = glob.glob(os.path.join(folder, "*"))
    for f in files:
        try:
            os.remove(f)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Failed to delete {f}: {e}")

@app.route("/predict", methods=["POST"])
def predict():

    try:
        data = request.json

        # ========================================
        # INPUT VALUES
        # ========================================

        stock = data["stock"]

        close = float(data["close"])
        volume = float(data["volume"])
        ma10 = float(data["ma10"])
        ma50 = float(data["ma50"])
        volatility = float(data["volatility"])
        gold = float(data["gold"])
        oil = float(data["oil"])
        vix = float(data["vix"])

        # ========================================
        # ENCODE STOCK
        # ========================================

        stock_encoded = encoder.transform([stock])[0]

        # ========================================
        # BUILD INPUT DF
        # ========================================

        input_df = pd.DataFrame([[
            close,
            volume,
            ma10,
            ma50,
            volatility,
            gold,
            oil,
            vix,
            stock_encoded
        ]], columns=features)

        # ========================================
        # PREDICTION
        # ========================================

        prediction = model.predict(input_df)[0]
        risk = risk_map[prediction]

        # ========================================
        # SHAP EXPLANATION (SAFE)
        # ========================================

        shap_values = explainer(input_df).values

        # handle shape safely
        if len(shap_values.shape) == 3:
            shap_values = shap_values[0][prediction]
        else:
            shap_values = shap_values[0]

        impact = dict(zip(features, shap_values))

        top_factors = sorted(
            impact.items(),
            key=lambda x: abs(float(x[1])),
            reverse=True
        )[:3]

        # ========================================
        # RESPONSE
        # ========================================

        return jsonify({
            "stock": stock,
            "risk": risk,
            "top_factors": [
                {"factor": k, "impact": float(v)}
                for k, v in top_factors
            ]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ============================================
# FETCH GLOBAL MARKET FACTORS
# ============================================

def get_global_market_data():

    # GOLD
    gold_df = yf.download(
        "GC=F",
        period="5d",
        progress=False
    )

    # OIL
    oil_df = yf.download(
        "CL=F",
        period="5d",
        progress=False
    )

    # VIX
    vix_df = yf.download(
        "^VIX",
        period="5d",
        progress=False
    )

    # 🔥 FIX MultiIndex if exists
    if isinstance(gold_df.columns, pd.MultiIndex):
        gold_df.columns = gold_df.columns.get_level_values(0)

    if isinstance(oil_df.columns, pd.MultiIndex):
        oil_df.columns = oil_df.columns.get_level_values(0)

    if isinstance(vix_df.columns, pd.MultiIndex):
        vix_df.columns = vix_df.columns.get_level_values(0)

    gold = float(gold_df["Close"].iloc[-1])
    oil = float(oil_df["Close"].iloc[-1])
    vix = float(vix_df["Close"].iloc[-1])

    return gold, oil, vix

# ============================================
# API ENDPOINT
# ============================================

@app.route("/predict_auto", methods=["POST"])
def predict_auto():

    try:

        data = request.json

        # ========================================
        # USER INPUTS
        # ========================================

        stock = data["stock"]

        close = float(data["close"])
        volume = float(data["volume"])
        ma10 = float(data["ma10"])
        ma50 = float(data["ma50"])
        volatility = float(data["volatility"])
        print(data)

        # ========================================
        # AUTO FETCH GLOBAL DATA
        # ========================================

        gold, oil, vix = get_global_market_data()

        # ========================================
        # ENCODE STOCK
        # ========================================

        stock_encoded = encoder.transform([stock])[0]

        # ========================================
        # BUILD INPUT DATAFRAME
        # ========================================

        input_df = pd.DataFrame([[
            close,
            volume,
            ma10,
            ma50,
            volatility,
            gold,
            oil,
            vix,
            stock_encoded
        ]], columns=features)

        # ========================================
        # MODEL PREDICTION
        # ========================================

        prediction = model.predict(input_df)[0]

        risk = risk_map[prediction]

        explainer_ai = StockAIExplainer()

        
        # ========================================
        # SHAP EXPLANATION
        # ========================================

        shap_values = explainer(input_df).values

        # Handle SHAP shape
        if len(shap_values.shape) == 3:
            shap_values = shap_values[0][prediction]
        else:
            shap_values = shap_values[0]

        impact = dict(zip(features, shap_values))

        top_factors = sorted(
            impact.items(),
            key=lambda x: abs(float(x[1])),
            reverse=True
        )[:3]

        ai_explanation = explainer_ai.explain(
            stock=stock,
            risk=risk,
            gold=gold,
            oil=oil,
            vix=vix,
            top_factors=[
                {
                    "factor": k,
                    "impact": float(v)
                }
                for k, v in top_factors
            ]
        )


        # ========================================
        # RESPONSE
        # ========================================

        # recommender_instance = social_recommender()

        # # Get recommendations
        # recommendations = recommender_instance.getRecommendations(pest_name)

        return jsonify({

            "stock": stock,

            "risk": risk,

            "market_data": {
                "gold": gold,
                "oil": oil,
                "vix": vix
            },

            "top_factors": [
                {
                    "factor": k,
                    "impact": float(v)
                }
                for k, v in top_factors
            ],

            "ai_explanation": ai_explanation
        })

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


# ============================================
# LIVE GLOBAL MARKET DATA API
# ============================================

@app.route("/market-data", methods=["GET"])
def market_data():

    try:

        # ========================================
        # DOWNLOAD MARKET DATA
        # ========================================

        gold_df = yf.download(
            "GC=F",
            period="5d",
            progress=False
        )

        oil_df = yf.download(
            "CL=F",
            period="5d",
            progress=False
        )

        vix_df = yf.download(
            "^VIX",
            period="5d",
            progress=False
        )

        # ========================================
        # FIX MULTI INDEX
        # ========================================

        if isinstance(gold_df.columns, pd.MultiIndex):
            gold_df.columns = gold_df.columns.get_level_values(0)

        if isinstance(oil_df.columns, pd.MultiIndex):
            oil_df.columns = oil_df.columns.get_level_values(0)

        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df.columns = vix_df.columns.get_level_values(0)

        # ========================================
        # GET LATEST VALUES
        # ========================================

        gold_price = float(gold_df["Close"].iloc[-1])
        oil_price = float(oil_df["Close"].iloc[-1])
        vix_value = float(vix_df["Close"].iloc[-1])

        latest_date = str(gold_df.index[-1])

        # ========================================
        # RESPONSE
        # ========================================

        return jsonify({

            "date": latest_date,

            "gold": {
                "symbol": "GC=F",
                "price": gold_price
            },

            "oil": {
                "symbol": "CL=F",
                "price": oil_price
            },

            "vix": {
                "symbol": "^VIX",
                "value": vix_value
            }

        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# @app.route('/download-cse')
# def download_cse():

#     options = webdriver.ChromeOptions()

#     prefs = {
#         "download.default_directory": r"C:\CSEDownloads"
#     }

#     options.add_experimental_option("prefs", prefs)

#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options
#     )

#     try:
#         driver.get("https://www.cse.lk/equity/trade-summary")

#         time.sleep(5)

#         download_btn = driver.find_element(
#             By.XPATH,
#             "//button[contains(text(),'Download')]"
#         )

#         download_btn.click()

#         time.sleep(10)

#         return jsonify({
#             "status": "success"
#         })

#     finally:
#         driver.quit()



# DOWNLOAD_FOLDER = r"D:\CSEDownloads"

# os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# @app.route('/download-cse', methods=['GET'])
# def download_cse():

#     options = webdriver.ChromeOptions()

#     prefs = {
#         "download.default_directory": DOWNLOAD_FOLDER,
#         "download.prompt_for_download": False,
#         "download.directory_upgrade": True,
#         "safebrowsing.enabled": True
#     }

#     options.add_experimental_option("prefs", prefs)

#     # Uncomment for background execution
#     # options.add_argument("--headless=new")

#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options
#     )

#     try:

#         driver.get("https://www.cse.lk/equity/trade-summary")

#         wait = WebDriverWait(driver, 30)

#         # Wait until page loads
#         wait.until(
#             lambda d: d.execute_script("return document.readyState") == "complete"
#         )

#         time.sleep(5)

#         # Click Download button
#         download_button = wait.until(
#             EC.element_to_be_clickable(
#                 (
#                     By.CSS_SELECTOR,
#                     "button[aria-label='Download options']"
#                 )
#             )
#         )

#         download_button.click()

#         print("Download button clicked")

#         time.sleep(3)

#         # Debug: print all menu text
#         elements = driver.find_elements(By.XPATH, "//*")
#         for e in elements:
#             try:
#                 txt = e.text.strip()
#                 if txt:
#                     print(txt)
#             except:
#                 pass

#         # Try clicking Excel option
#         excel_option = wait.until(
#             EC.element_to_be_clickable(
#                 (
#                     By.XPATH,
#                     "//*[contains(text(),'Excel')]"
#                 )
#             )
#         )

#         excel_option.click()

#         print("Excel option clicked")

#         # Wait for download
#         time.sleep(15)

#         downloaded_files = os.listdir(DOWNLOAD_FOLDER)

#         return jsonify({
#             "status": "success",
#             "download_folder": DOWNLOAD_FOLDER,
#             "files": downloaded_files
#         })

#     except Exception as ex:

#         driver.save_screenshot("cse_error.png")

#         with open("cse_page.html", "w", encoding="utf-8") as f:
#             f.write(driver.page_source)

#         return jsonify({
#             "status": "error",
#             "message": str(ex)
#         })

#     finally:
#         driver.quit()
        


DOWNLOAD_FOLDER = r"D:\Research\0032 - Stock\0032 - Stock\Backend\Download"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# @app.route('/download-cse', methods=['GET'])
# def download_cse():

#     options = Options()

#     prefs = {
#         "download.default_directory": DOWNLOAD_FOLDER,
#         "download.prompt_for_download": False,
#         "download.directory_upgrade": True,
#         "safebrowsing.enabled": True
#     }

#     options.add_experimental_option("prefs", prefs)

#     # options.add_argument("--headless=new")  # optional

#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options
#     )

#     wait = WebDriverWait(driver, 30)

#     try:
#         driver.get("https://www.cse.lk/equity/trade-summary")

#         # wait page load
#         wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

#         # wait download button
#         download_btn = wait.until(
#             EC.element_to_be_clickable(
#                 (By.CSS_SELECTOR, "button[aria-label='Download options']")
#             )
#         )

#         download_btn.click()
#         print("Download dropdown opened")

#         # IMPORTANT: wait for dropdown menu to appear
#         csv_btn = wait.until(
#             EC.visibility_of_element_located(
#                 (By.XPATH, "//button[normalize-space()='CSV']")
#             )
#         )

#         # scroll into view (important for some layouts)
#         driver.execute_script("arguments[0].scrollIntoView(true);", csv_btn)

#         wait.until(EC.element_to_be_clickable(
#             (By.XPATH, "//button[normalize-space()='CSV']")
#         )).click()

#         print("CSV clicked")

#         # wait download complete (better: poll folder)
#         time.sleep(10)

#         files = os.listdir(DOWNLOAD_FOLDER)

#         return jsonify({
#             "status": "success",
#             "download_folder": DOWNLOAD_FOLDER,
#             "files": files
#         })

#     except Exception as ex:
#         driver.save_screenshot("cse_error.png")

#         with open("cse_page.html", "w", encoding="utf-8") as f:
#             f.write(driver.page_source)

#         return jsonify({
#             "status": "error",
#             "message": str(ex)
#         })

#     finally:
#         driver.quit()



# @app.route('/download-cse', methods=['GET'])
# def download_cse():

#     options = Options()

#     prefs = {
#         "download.default_directory": DOWNLOAD_FOLDER,
#         "download.prompt_for_download": False,
#         "download.directory_upgrade": True,
#         "safebrowsing.enabled": True
#     }

#     options.add_experimental_option("prefs", prefs)

#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options
#     )

#     wait = WebDriverWait(driver, 30)

#     try:
#         driver.get("https://www.cse.lk/equity/trade-summary")

#         wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

#         # -------------------------------
#         # STEP 1: SET ROWS = ALL
#         # -------------------------------
#         try:
#             rows_dropdown = wait.until(
#                 EC.element_to_be_clickable((
#                     By.XPATH,
#                     "//button[.//span[normalize-space()='All'] or contains(.,'25')]"
#                 ))
#             )

#             rows_dropdown.click()
#             print("Rows dropdown opened")

#             # click "All"
#             all_option = wait.until(
#                 EC.element_to_be_clickable((
#                     By.XPATH,
#                     "//span[normalize-space()='All']"
#                 ))
#             )

#             all_option.click()
#             print("Selected All rows")

#             # wait for table refresh
#             time.sleep(5)

#         except Exception as e:
#             print("Rows selection failed, continuing anyway:", str(e))

#         # -------------------------------
#         # STEP 2: OPEN DOWNLOAD MENU
#         # -------------------------------
#         download_btn = wait.until(
#             EC.element_to_be_clickable((
#                 By.CSS_SELECTOR,
#                 "button[aria-label='Download options']"
#             ))
#         )

#         download_btn.click()
#         print("Download menu opened")

#         # -------------------------------
#         # STEP 3: CLICK CSV
#         # -------------------------------
#         csv_btn = wait.until(
#             EC.element_to_be_clickable((
#                 By.XPATH,
#                 "//button[normalize-space()='CSV']"
#             ))
#         )

#         csv_btn.click()
#         print("CSV download started")

#         # wait for download
#         time.sleep(10)

#         files = os.listdir(DOWNLOAD_FOLDER)

#         return jsonify({
#             "status": "success",
#             "files": files
#         })

#     except Exception as ex:

#         driver.save_screenshot("cse_error.png")

#         with open("cse_page.html", "w", encoding="utf-8") as f:
#             f.write(driver.page_source)

#         return jsonify({
#             "status": "error",
#             "message": str(ex)
#         })

#     finally:
#         driver.quit()

def normalize(text):
    if not isinstance(text, str):
        return ""

    # remove extra spaces, trim, lowercase
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text
    

@app.route('/download-cse', methods=['GET'])
def download_cse():

    options = Options()

    prefs = {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    clear_old_files(DOWNLOAD_FOLDER)

    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    wait = WebDriverWait(driver, 30)

    try:
        driver.get("https://www.cse.lk/equity/trade-summary")

        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        # =========================================================
        # STEP 1: CLICK ROWS DROPDOWN (CURRENT 25 → CHANGE TO ALL)
        # =========================================================

        try:
            rows_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class,'h-10') and .//span]"
                ))
            )

            driver.execute_script("arguments[0].click();", rows_btn)
            print("Rows dropdown opened")

            # wait menu render
            time.sleep(1.5)

            # IMPORTANT: click BUTTON (not span)
            all_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[contains(@class,'overflow-hidden')]//button[.//text()[contains(.,'All')]]"
                ))
            )

            driver.execute_script("arguments[0].click();", all_btn)
            print("Selected ALL rows")

            time.sleep(5)  # table refresh wait

        except Exception as e:
            print("Rows dropdown failed but continuing:", str(e))

        # =========================================================
        # STEP 2: OPEN DOWNLOAD DROPDOWN
        # =========================================================

        download_btn = wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "button[aria-label='Download options']"
            ))
        )

        driver.execute_script("arguments[0].click();", download_btn)
        print("Download menu opened")

        # =========================================================
        # STEP 3: CLICK CSV
        # =========================================================

        csv_btn = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class,'overflow-hidden')]//button[normalize-space()='CSV']"
            ))
        )

        driver.execute_script("arguments[0].click();", csv_btn)
        print("CSV download triggered")

        time.sleep(10)

        files = os.listdir(DOWNLOAD_FOLDER)

        return jsonify({
            "status": "success",
            "files": files
        })

    except Exception as ex:

        driver.save_screenshot("cse_error.png")

        with open("cse_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        return jsonify({
            "status": "error",
            "message": str(ex)
        })

    finally:
        driver.quit()


TARGET_COMPANIES = [
    "HEMAS HOLDINGS PLC",
    "JOHN KEELLS HOLDINGS PLC",
    "CHEVRON LUBRICANTS LANKA PLC"
    ""
]

# -------------------------------------------------
# Helper: Get latest CSV file
# -------------------------------------------------
def get_latest_csv(folder):
    files = glob.glob(os.path.join(folder, "*.csv"))

    if not files:
        return None

    latest_file = max(files, key=os.path.getctime)
    return latest_file


# -------------------------------------------------
# API: Filter Company Data
# -------------------------------------------------
# @app.route("/cse-filter", methods=["GET"])
# def cse_filter():

#     try:
#         file_path = get_latest_csv(DOWNLOAD_FOLDER)

#         if not file_path:
#             return jsonify({
#                 "status": "error",
#                 "message": "No CSV file found"
#             })

#         df = pd.read_csv(file_path)

#         # Normalize column names (important for real-world CSVs)
#         df.columns = [col.strip() for col in df.columns]

#         # Try to detect Company Name column safely
#         possible_columns = ["Company Name", "COMPANY NAME", "company name"]

#         company_col = None
#         for col in df.columns:
#             if col.strip().lower() == "company name":
#                 company_col = col
#                 break

#         if not company_col:
#             return jsonify({
#                 "status": "error",
#                 "message": "Company Name column not found",
#                 "columns": list(df.columns)
#             })

#         # Filter data
#         # normalize target companies
#         normalized_targets = [normalize(x) for x in TARGET_COMPANIES]

#         # normalize CSV column
#         df["normalized_company"] = df[company_col].apply(normalize)

#         # filter
#         filtered_df = df[df["normalized_company"].isin(normalized_targets)]

#         # # drop helper column
#         # filtered_df = filtered_df.drop(columns=["normalized_company"])

#         # Convert to JSON
#         result = filtered_df.to_dict(orient="records")

#         return jsonify({
#             "status": "success",
#             "file_used": file_path,
#             "count": len(result),
#             "data": result
#         })

#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": str(e)
#         })



# @app.route("/cse-filter", methods=["GET"])
# def cse_filter():

#     try:

#         file_path = get_latest_csv(DOWNLOAD_FOLDER)

#         if not file_path:
#             return jsonify({
#                 "status": "error",
#                 "message": "No CSV file found"
#             })


#         df = pd.read_csv(file_path)


#         # Clean column names
#         df.columns = [col.strip() for col in df.columns]


#         # Find company column
#         company_col = None

#         for col in df.columns:
#             if col.lower().strip() == "company name":
#                 company_col = col
#                 break


#         if not company_col:
#             return jsonify({
#                 "status": "error",
#                 "message": "Company Name column not found"
#             })


#         # Normalize company names

#         normalized_targets = [
#             normalize(x) for x in TARGET_COMPANIES
#         ]


#         df["normalized_company"] = (
#             df[company_col]
#             .apply(normalize)
#         )


#         # Filter companies

#         filtered_df = df[
#             df["normalized_company"]
#             .isin(normalized_targets)
#         ]


#         # ============================
#         # ADD DATE
#         # ============================

#         today = datetime.now().strftime("%Y/%m/%d")


#         filtered_df["date"] = today


#         # Convert dataframe to json

#         records = filtered_df.to_dict(
#             orient="records"
#         )


#         # ============================
#         # SAVE TO MONGODB
#         # ============================

#         if records:

#             for item in records:

#                 # avoid duplicate same day
#                 existing = stock_collection.find_one({
#                     "Symbol": item.get("Symbol"),
#                     "date": today
#                 })


#                 if existing:

#                     # update existing record
#                     stock_collection.update_one(
#                         {
#                             "_id": existing["_id"]
#                         },
#                         {
#                             "$set": item
#                         }
#                     )

#                 else:

#                     stock_collection.insert_one(item)



#         return jsonify({

#             "status": "success",

#             "saved_to_mongodb": True,

#             "date": today,

#             "count": len(records),

#             "data": records

#         })


#     except Exception as e:


#         return jsonify({

#             "status":"error",

#             "message":str(e)

#         }),500

@app.route("/cse-filter", methods=["GET"])
def cse_filter():

    try:

        file_path = get_latest_csv(DOWNLOAD_FOLDER)

        if not file_path:
            return jsonify({
                "status": "error",
                "message": "No CSV file found"
            })


        # ============================
        # READ CSV
        # ============================

        df = pd.read_csv(file_path)


        # Clean columns
        df.columns = [
            col.strip()
            for col in df.columns
        ]


        # ============================
        # FIND COMPANY COLUMN
        # ============================

        company_col = None

        for col in df.columns:

            if col.lower().strip() == "company name":
                company_col = col
                break


        if not company_col:

            return jsonify({
                "status": "error",
                "message": "Company Name column not found",
                "columns": list(df.columns)
            })



        # ============================
        # FILTER COMPANIES
        # ============================

        normalized_targets = [
            normalize(x)
            for x in TARGET_COMPANIES
        ]


        df["normalized_company"] = (
            df[company_col]
            .apply(normalize)
        )


        filtered_df = df[
            df["normalized_company"]
            .isin(normalized_targets)
        ]



        # ============================
        # ADD DATE
        # ============================

        today = datetime.now().strftime("%Y/%m/%d")


        filtered_df["date"] = today

        # custom_date = "2026/06/05"

        # filtered_df["date"] = custom_date



        records = filtered_df.to_dict(
            orient="records"
        )



        # ============================
        # REMOVE TODAY OLD DATA
        # ============================

        delete_result = stock_collection.delete_many(
            {
                "date": today
            }
        )


        print(
            f"Deleted {delete_result.deleted_count} old records for {today}"
        )



        # ============================
        # INSERT NEW DATA
        # ============================

        if records:

            result = stock_collection.insert_many(records)

            # add MongoDB ids if needed
            for i, item in enumerate(records):
                item["_id"] = str(result.inserted_ids[i])



            return jsonify({

            "status": "success",

            "date": today,

            "deleted_old_records": 
                delete_result.deleted_count,

            "inserted_records":
                len(records),

            "data": records

        })

    except Exception as e:


        return jsonify({

            "status": "error",

            "message": str(e)

        }),500



@app.route("/ma10/<symbol>", methods=["GET"])
def get_ma10(symbol):

    try:

        today = datetime.now().strftime("%Y/%m/%d")

        # Get last 10 records excluding today
        records = list(
            stock_collection.find(
                {
                    "Symbol": symbol,
                    "date": {"$ne": today}
                },
                {
                    "_id": 0
                }
            )
            .sort("date", -1)
            .limit(10)
        )

        if len(records) == 0:

            return jsonify({
                "status": "error",
                "message": "No historical data found"
            })

        closes = []

        for record in records:

            value = record.get("**Last Trade (Rs.)")

            if value is not None:
                closes.append(float(value))

        if len(closes) == 0:

            return jsonify({
                "status": "error",
                "message": "No close values found"
            })

        ma10 = sum(closes) / len(closes)

        return jsonify({

            "status": "success",

            "symbol": symbol,

            "days_used": len(closes),

            "ma10": round(ma10, 4),

            "close_values": closes

        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/ma50/<symbol>", methods=["GET"])
def get_ma50(symbol):

    try:

        today = datetime.now().strftime("%Y/%m/%d")

        # Get last 50 records excluding today
        records = list(
            stock_collection.find(
                {
                    "Symbol": symbol,
                    "date": {"$ne": today}
                },
                {
                    "_id": 0
                }
            )
            .sort("date", -1)
            .limit(50)
        )

        if len(records) == 0:

            return jsonify({
                "status": "error",
                "message": "No historical data found"
            })

        closes = []

        for record in records:

            value = record.get("**Last Trade (Rs.)")

            if value is not None:
                closes.append(float(value))

        if len(closes) == 0:

            return jsonify({
                "status": "error",
                "message": "No close values found"
            })

        ma50 = sum(closes) / len(closes)

        return jsonify({

            "status": "success",

            "symbol": symbol,

            "days_used": len(closes),

            "ma50": round(ma50, 4),

            "close_values": closes

        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/volatility/<symbol>", methods=["GET"])
def get_volatility(symbol):

    try:

        today = datetime.now().strftime("%Y/%m/%d")


        # Get last 10 days excluding today
        records = list(
            stock_collection.find(
                {
                    "Symbol": symbol,
                    "date": {"$ne": today}
                },
                {
                    "_id": 0
                }
            )
            .sort("date", -1)
            .limit(10)
        )


        if len(records) == 0:

            return jsonify({
                "status": "error",
                "message": "No historical data found"
            })


        closes = []


        for item in records:

            close = item.get("**Last Trade (Rs.)")

            if close is not None:
                closes.append(float(close))


        if len(closes) < 2:

            return jsonify({
                "status": "error",
                "message": "Not enough data for volatility"
            })


        # Calculate volatility
        volatility = pd.Series(closes).std()


        return jsonify({

            "status": "success",

            "symbol": symbol,

            "days_used": len(closes),

            "volatility": round(float(volatility), 4),

            "close_values": closes

        })


    except Exception as e:

        return jsonify({
            "status":"error",
            "message":str(e)
        }),500
    
# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    app.run(debug=True)