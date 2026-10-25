# from langchain_core.prompts import PromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_google_genai import ChatGoogleGenerativeAI
# import google.generativeai as genai

# GOOGLE_API_KEY = "AIzaSyACaLdWtI-_h74nuu25VPQy3Vr5UgtF0Ic"
# genai.configure(api_key=GOOGLE_API_KEY)

# class ai_recommender:
#     def __init__(self, model_name="gemini-flash-lite-latest"):
#         self.__model = ChatGoogleGenerativeAI(
#             model=model_name,  # <-- safe model
#             temperature=0.7,
#             google_api_key=GOOGLE_API_KEY
#         )

#         self.__output_parser = StrOutputParser()
#         self.__template = (
#             "I am currently experiencing {stress_level} social stress. Can you provide practical steps, exercises, or strategies to manage and reduce social stress in daily life, including ways to stay calm, communicate better, and handle social situations more confidently. give me 3 steps for this within less than 500 words"
#         )
#         self.__prompt_template = PromptTemplate(
#             template=self.__template,
#             input_variables=["stress_level"]
#         )

#     def getRecommendations(self, stress_level: str) -> list[str]:
#         chain = self.__prompt_template | self.__model | self.__output_parser
#         recommendations = chain.invoke({"stress_level": stress_level})
#         return recommendations

# from langchain_core.prompts import PromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_google_genai import ChatGoogleGenerativeAI
# import google.generativeai as genai

# GOOGLE_API_KEY = "AIzaSyACaLdWtI-_h74nuu25VPQy3Vr5UgtF0Ic"

# genai.configure(api_key=GOOGLE_API_KEY)


# class StockAIExplainer:

#     def __init__(self, model_name="gemini-flash-lite-latest"):

#         self.model = ChatGoogleGenerativeAI(
#             model=model_name,
#             temperature=0.3,
#             google_api_key=GOOGLE_API_KEY
#         )

#         self.output_parser = StrOutputParser()

#         self.template = """
# You are a professional stock market analyst.

# A machine learning model predicted the investment risk for a stock.

# Explain the prediction in simple English so that someone with little stock market knowledge can understand it.

# Stock Information

# Stock Symbol:
# {stock}

# Predicted Risk:
# {risk}

# Global Market

# Gold Price:
# {gold}

# Oil Price:
# {oil}

# VIX Index:
# {vix}

# Top Features Influencing the Prediction

# {top_factors}

# Instructions

# - Explain what the predicted risk means.
# - Explain why these top factors affected the prediction.
# - Explain the current market conditions using Gold, Oil and VIX.
# - Mention whether the market looks calm or volatile.
# - Do NOT mention SHAP values or machine learning terminology.
# - Do NOT talk about model confidence.
# - Keep the explanation friendly and professional.
# - Maximum 250 words.
# - Finish with a short investment caution saying this is not financial advice.
# """

#         self.prompt = PromptTemplate(
#             template=self.template,
#             input_variables=[
#                 "stock",
#                 "risk",
#                 "gold",
#                 "oil",
#                 "vix",
#                 "top_factors"
#             ]
#         )

#     def explain(
#         self,
#         stock,
#         risk,
#         gold,
#         oil,
#         vix,
#         top_factors
#     ):

#         formatted = "\n".join(
#             [
#                 f"- {item['factor']}: impact {item['impact']:.5f}"
#                 for item in top_factors
#             ]
#         )

#         chain = self.prompt | self.model | self.output_parser

#         return chain.invoke(
#             {
#                 "stock": stock,
#                 "risk": risk,
#                 "gold": gold,
#                 "oil": oil,
#                 "vix": vix,
#                 "top_factors": formatted
#             }
#         )

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import traceback

GOOGLE_API_KEY = "AIzaSyACaLdWtI-_h74nuu25VPQy3Vr5UgtF0Ic"

genai.configure(api_key=GOOGLE_API_KEY)


class StockAIExplainer:

    def __init__(self, model_name="gemini-2.5-flash"):

        print("===== Initializing StockAIExplainer =====")

        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.3,
            google_api_key=GOOGLE_API_KEY
        )

        print("Gemini model initialized successfully.")

        self.output_parser = StrOutputParser()

        self.template = """
You are a professional stock market analyst.

A machine learning model predicted the investment risk for a stock.

Explain the prediction in simple English so that someone with little stock market knowledge can understand it.

Stock Information

Stock Symbol:
{stock}

Predicted Risk:
{risk}

Global Market

Gold Price:
{gold}

Oil Price:
{oil}

VIX Index:
{vix}

Top Features Influencing the Prediction

{top_factors}

Instructions

- Explain what the predicted risk means.
- Explain why these top factors affected the prediction.
- Explain the current market conditions using Gold, Oil and VIX.
- Mention whether the market looks calm or volatile.
- Do NOT mention SHAP values or machine learning terminology.
- Do NOT talk about model confidence.
- Keep the explanation friendly and professional.
- Maximum 250 words.
- Finish with a short investment caution saying this is not financial advice.
"""

        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=[
                "stock",
                "risk",
                "gold",
                "oil",
                "vix",
                "top_factors"
            ]
        )

    def explain(
        self,
        stock,
        risk,
        gold,
        oil,
        vix,
        top_factors
    ):

        try:

            print("\n========== AI INPUT ==========")
            print("Stock :", stock)
            print("Risk  :", risk)
            print("Gold  :", gold)
            print("Oil   :", oil)
            print("VIX   :", vix)
            print("Top Factors :", top_factors)

            formatted = "\n".join(
                [
                    f"- {item['factor']}: impact {item['impact']:.5f}"
                    for item in top_factors
                ]
            )

            print("\n========== FORMATTED ==========")
            print(formatted)

            chain = self.prompt | self.model | self.output_parser

            print("\nCalling Gemini...")

            final_prompt = self.prompt.format(
            stock=stock,
            risk=risk,
            gold=gold,
            oil=oil,
            vix=vix,
            top_factors=formatted
            )

            print("\n========== FINAL PROMPT ==========")
            print(final_prompt)
            print("===================================")

            response = chain.invoke(
                {
                    "stock": stock,
                    "risk": risk,
                    "gold": gold,
                    "oil": oil,
                    "vix": vix,
                    "top_factors": formatted
                }
            )

            print("\n========== GEMINI RESPONSE ==========")
            print(response)

            return response

        except Exception as e:

            print("\n========== GEMINI ERROR ==========")
            traceback.print_exc()
            print(e)

            raise