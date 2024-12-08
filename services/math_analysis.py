from datetime import datetime, timedelta

import aiohttp
import asyncio
import numpy as np
import pandas as pd
from scipy.stats import linregress
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from typing import List, Dict, Any, Optional


class AuctionItemAnalyzerAsync:
    BASE_URL = "https://eapi.stalcraft.net"

    def __init__(self, region: str, item: str, token_user: str):
        self.region = region
        self.item = item
        self.token_user = token_user

    async def _fetch_data(self, session: aiohttp.ClientSession, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Асинхронный метод для выполнения запросов к API.

        :param session: Асинхронная сессия aiohttp.
        :param endpoint: Конечная точка API.
        :param params: Параметры запроса.
        :return: Ответ в виде словаря.
        """
        url = f"{self.BASE_URL}/{self.region}/auction/{self.item}/{endpoint}"
        async with session.get(url,
                               headers=
                               {
                                   'Authorization': f"Bearer {self.token_user}",
                                   'Content-Type': "application/json",
                               },

                               params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def get_price_history(self, session: aiohttp.ClientSession, limit: int = 200, offset: int = 0) -> pd.DataFrame:
        params = {"limit": limit, "offset": offset, "additional": "false"}
        print(f"я даун1 {params}")
        data = await self._fetch_data(session, "history", params)
        print(f"я даун2 {data}")
        prices = data.get("prices", [])
        print(f"я даун3 {prices}")
        print(f"я даун4 {pd.DataFrame(prices)}")
        result = pd.DataFrame(prices)
        if not prices:
            return pd.DataFrame()
        return result

    async def get_active_lots(self, session: aiohttp.ClientSession, limit: int = 200, offset: int = 0) -> pd.DataFrame:
        params = {
            "limit": limit,
            "offset": offset,
            "additional": "false",
            "order": "asc",
            "sort": "buyout_price",
        }
        print(f"я проверяю1 {params}")
        data = await self._fetch_data(session, "lots", params)
        print(f"я проверяю2 {data}")
        lots = data.get("lots", [])
        print(f"я проверяю3 {lots}")
        print(f"я проверяю4 {pd.DataFrame(lots)}")
        df = pd.DataFrame(lots)
        result = df.to_dict()
        if not lots:
            return result
        return result

    def analyze_trend(self, history: pd.DataFrame) -> Dict[str, Any]:
        if history.empty:
            return {"trend": "No data available"}

        history["timestamp"] =  pd.to_datetime(history["time"]).astype(np.int64) // 10**9
        prices = history["price"].values
        timestamps = history["timestamp"].values

        slope, intercept, r_value, _, _ =  linregress(timestamps, prices)
        trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"

        return {
            "trend": trend,
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_value**2,
        }

    def predict_future_price(self, history: pd.DataFrame, days_ahead: int = 7) -> Dict[str, Any]:
        if history.empty:
            return {"prediction": "No data available"}

        # Преобразование времени в timestamp
        try:
            history["timestamp"] = pd.to_datetime(history["time"]).view(np.int64) // 10 ** 9
        except Exception as e:
            return {"error": f"Failed to process time column: {str(e)}"}

        # Проверка данных
        prices = history["price"].values
        timestamps = history["timestamp"].values

        if len(prices) < 2 or len(timestamps) < 2:
            return {"prediction": "Not enough data for prediction"}

        try:
            # Преобразование данных в правильный формат
            timestamps = timestamps.reshape(-1, 1).astype(float)  # Явное приведение к float
            prices = prices.reshape(-1, 1).astype(float)

            # Полиномиальная регрессия
            poly = PolynomialFeatures(degree=2)
            timestamps_poly = poly.fit_transform(timestamps)
            model = LinearRegression().fit(timestamps_poly, prices)

            # Генерация будущей отметки времени
            future_timestamp = timestamps[-1][0] + days_ahead * 86400
            future_timestamp_poly = poly.transform([[future_timestamp]])

            # Предсказание
            future_price = model.predict(future_timestamp_poly)[0][0]

            return {
                "future_price": round(float(max(future_price, 0)), 2),  # Приведение к float с округлением
                "model_coefficients": [round(float(c), 6) for c in model.coef_.flatten()],  # Приведение коэффициентов
                "intercept": round(float(model.intercept_[0]), 2),  # Приведение к float с округлением
            }
        except Exception as e:
            return {"error": f"Prediction failed: {str(e)}"}

    def analyze_selling_price(self, history: pd.DataFrame) -> Dict[str, Any]:
        if history.empty:
            return {"recommendation": "No price history found"}

        avg_price = history["price"].mean()
        std_dev = history["price"].std()
        return {
            "recommendation": "Suggested selling price",
            "average_price": avg_price,
            "suggested_price": avg_price + std_dev,
            "std_dev": std_dev,
        }

    async def analyze_purchase_opportunity(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        lots = await self.get_active_lots(session)
        lots = pd.DataFrame(lots)
        if lots.empty:
            return {"recommendation": "No active lots found"}

        cheapest_lot = lots.loc[lots["buyoutPrice"].idxmin()]
        print(type(cheapest_lot))
        print(cheapest_lot)
        print("я непонятная хуйня!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(cheapest_lot["buyoutPrice"])
        print(cheapest_lot["amount"])
        print("2я непонятная хуйня!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        result = cheapest_lot["buyoutPrice"]
        print(type(result))

        return {
            "recommendation": "Consider buying",
            "cheapest_buyout_price": str(cheapest_lot["buyoutPrice"]),
            "amount": str(cheapest_lot["amount"]),
        }

    async def get_analysis_report(self) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            price_history_task = await self.get_price_history(session)
            purchase_task = await self.analyze_purchase_opportunity(session)
            get_active_lots = await self.get_active_lots(session)

            history = await self.get_price_history(session)




            trend_analysis = self.analyze_trend(history)
            future_price_prediction = self.predict_future_price(history)

            selling_recommendation = self.analyze_selling_price(history)

            return {
                "get_active_lots": get_active_lots,
                "get_history": price_history_task.to_dict(),
                "purchase_analysis": purchase_task,
                "selling_analysis": selling_recommendation,
                "trend_analysis": trend_analysis,
                "future_price_prediction": future_price_prediction,
            }


# Пример использования:
#async def main():
#    analyzer = AuctionItemAnalyzerAsync(region="eu", item="y1q9")
#    report = await analyzer.get_analysis_report()
#    print(report)

