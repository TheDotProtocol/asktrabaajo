import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from api.models.database import Currency
from api.models.schemas import CurrencyUpdate, SalaryConversionRequest

logger = logging.getLogger(__name__)

class CurrencyService:
    def __init__(self):
        self.exchange_rate_api_url = "https://api.exchangerate-api.com/v4/latest/USD"
        self.crypto_api_url = "https://api.coingecko.com/api/v3"
        self.cache_duration = timedelta(hours=1)
        self.exchange_rates_cache = {}
        self.last_update = None
        
        # Supported currencies
        self.supported_currencies = {
            "USD": {"name": "US Dollar", "symbol": "$", "is_crypto": False},
            "EUR": {"name": "Euro", "symbol": "€", "is_crypto": False},
            "THB": {"name": "Thai Baht", "symbol": "฿", "is_crypto": False},
            "GBP": {"name": "British Pound", "symbol": "£", "is_crypto": False},
            "JPY": {"name": "Japanese Yen", "symbol": "¥", "is_crypto": False},
            "SGD": {"name": "Singapore Dollar", "symbol": "S$", "is_crypto": False},
            "AUD": {"name": "Australian Dollar", "symbol": "A$", "is_crypto": False},
            "CAD": {"name": "Canadian Dollar", "symbol": "C$", "is_crypto": False},
            "CHF": {"name": "Swiss Franc", "symbol": "CHF", "is_crypto": False},
            "CNY": {"name": "Chinese Yuan", "symbol": "¥", "is_crypto": False},
            "BTC": {"name": "Bitcoin", "symbol": "₿", "is_crypto": True},
            "ETH": {"name": "Ethereum", "symbol": "Ξ", "is_crypto": True},
            "USDT": {"name": "Tether", "symbol": "₮", "is_crypto": True},
            "BNB": {"name": "Binance Coin", "symbol": "BNB", "is_crypto": True},
            "3DOT": {"name": "3DOT Token", "symbol": "3DOT", "is_crypto": True},
            "ARHC": {"name": "ARHC Token", "symbol": "ARHC", "is_crypto": True}
        }
    
    async def initialize_currencies(self, db: Session) -> List[Currency]:
        """Initialize supported currencies in the database."""
        try:
            currencies = []
            for code, info in self.supported_currencies.items():
                # Check if currency already exists
                existing = db.query(Currency).filter(Currency.code == code).first()
                if not existing:
                    currency = Currency(
                        code=code,
                        name=info["name"],
                        symbol=info["symbol"],
                        exchange_rate_usd=1.0 if code == "USD" else 0.0,
                        is_active=True,
                        is_crypto=info["is_crypto"]
                    )
                    db.add(currency)
                    currencies.append(currency)
            
            db.commit()
            logger.info(f"Initialized {len(currencies)} new currencies")
            return currencies
            
        except Exception as e:
            logger.error(f"Error initializing currencies: {e}")
            db.rollback()
            raise
    
    async def update_exchange_rates(self, db: Session) -> Dict[str, float]:
        """Update exchange rates from external APIs."""
        try:
            # Update fiat currencies
            fiat_rates = await self._fetch_fiat_rates()
            
            # Update crypto currencies
            crypto_rates = await self._fetch_crypto_rates()
            
            # Combine rates
            all_rates = {**fiat_rates, **crypto_rates}
            
            # Update database
            updated_currencies = []
            for code, rate in all_rates.items():
                currency = db.query(Currency).filter(Currency.code == code).first()
                if currency:
                    currency.exchange_rate_usd = rate
                    currency.updated_at = datetime.utcnow()
                    updated_currencies.append(currency)
            
            db.commit()
            
            # Update cache
            self.exchange_rates_cache = all_rates
            self.last_update = datetime.utcnow()
            
            logger.info(f"Updated exchange rates for {len(updated_currencies)} currencies")
            return all_rates
            
        except Exception as e:
            logger.error(f"Error updating exchange rates: {e}")
            db.rollback()
            raise
    
    async def _fetch_fiat_rates(self) -> Dict[str, float]:
        """Fetch fiat currency exchange rates."""
        try:
            response = requests.get(self.exchange_rate_api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rates = data.get("rates", {})
            
            # Add USD rate
            rates["USD"] = 1.0
            
            return rates
            
        except Exception as e:
            logger.error(f"Error fetching fiat rates: {e}")
            return {}
    
    async def _fetch_crypto_rates(self) -> Dict[str, float]:
        """Fetch cryptocurrency exchange rates."""
        try:
            crypto_ids = ["bitcoin", "ethereum", "tether", "binancecoin"]
            crypto_codes = ["BTC", "ETH", "USDT", "BNB"]
            
            response = requests.get(
                f"{self.crypto_api_url}/simple/price",
                params={
                    "ids": ",".join(crypto_ids),
                    "vs_currencies": "usd"
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            rates = {}
            
            for i, crypto_id in enumerate(crypto_ids):
                if crypto_id in data and "usd" in data[crypto_id]:
                    rates[crypto_codes[i]] = data[crypto_id]["usd"]
            
            # Add custom crypto rates (placeholder values)
            rates["3DOT"] = 0.1  # Placeholder
            rates["ARHC"] = 0.05  # Placeholder
            
            return rates
            
        except Exception as e:
            logger.error(f"Error fetching crypto rates: {e}")
            return {}
    
    async def convert_salary(
        self, 
        conversion_request: SalaryConversionRequest, 
        db: Session
    ) -> Dict[str, Any]:
        """Convert salary between currencies."""
        try:
            # Get current exchange rates
            if not self._is_cache_valid():
                await self.update_exchange_rates(db)
            
            from_rate = self.exchange_rates_cache.get(conversion_request.from_currency, 0)
            to_rate = self.exchange_rates_cache.get(conversion_request.to_currency, 0)
            
            if from_rate == 0 or to_rate == 0:
                return {
                    "error": f"Exchange rate not available for {conversion_request.from_currency} or {conversion_request.to_currency}"
                }
            
            # Convert to USD first, then to target currency
            usd_amount = conversion_request.amount / from_rate
            converted_amount = usd_amount * to_rate
            
            return {
                "original_amount": conversion_request.amount,
                "original_currency": conversion_request.from_currency,
                "converted_amount": round(converted_amount, 2),
                "converted_currency": conversion_request.to_currency,
                "exchange_rate": round(to_rate / from_rate, 6),
                "conversion_date": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error converting salary: {e}")
            return {"error": str(e)}
    
    async def get_currency_info(self, currency_code: str, db: Session) -> Optional[Currency]:
        """Get currency information."""
        return db.query(Currency).filter(Currency.code == currency_code).first()
    
    async def get_all_currencies(self, db: Session) -> List[Currency]:
        """Get all active currencies."""
        return db.query(Currency).filter(Currency.is_active == True).all()
    
    async def get_fiat_currencies(self, db: Session) -> List[Currency]:
        """Get all fiat currencies."""
        return db.query(Currency).filter(
            Currency.is_active == True,
            Currency.is_crypto == False
        ).all()
    
    async def get_crypto_currencies(self, db: Session) -> List[Currency]:
        """Get all cryptocurrency currencies."""
        return db.query(Currency).filter(
            Currency.is_active == True,
            Currency.is_crypto == True
        ).all()
    
    async def update_currency(
        self, 
        currency_code: str, 
        update_data: CurrencyUpdate, 
        db: Session
    ) -> Optional[Currency]:
        """Update currency information."""
        try:
            currency = db.query(Currency).filter(Currency.code == currency_code).first()
            if not currency:
                return None
            
            if update_data.exchange_rate_usd is not None:
                currency.exchange_rate_usd = update_data.exchange_rate_usd
            
            if update_data.is_active is not None:
                currency.is_active = update_data.is_active
            
            currency.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(currency)
            
            return currency
            
        except Exception as e:
            logger.error(f"Error updating currency: {e}")
            db.rollback()
            return None
    
    async def get_salary_range_conversion(
        self, 
        min_salary: float, 
        max_salary: float, 
        from_currency: str, 
        to_currency: str, 
        db: Session
    ) -> Dict[str, Any]:
        """Convert salary range between currencies."""
        try:
            min_conversion = await self.convert_salary(
                SalaryConversionRequest(
                    amount=min_salary,
                    from_currency=from_currency,
                    to_currency=to_currency
                ),
                db
            )
            
            max_conversion = await self.convert_salary(
                SalaryConversionRequest(
                    amount=max_salary,
                    from_currency=from_currency,
                    to_currency=to_currency
                ),
                db
            )
            
            if "error" in min_conversion or "error" in max_conversion:
                return {"error": "Conversion failed"}
            
            return {
                "original_range": {
                    "min": min_salary,
                    "max": max_salary,
                    "currency": from_currency
                },
                "converted_range": {
                    "min": min_conversion["converted_amount"],
                    "max": max_conversion["converted_amount"],
                    "currency": to_currency
                },
                "exchange_rate": min_conversion["exchange_rate"],
                "conversion_date": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error converting salary range: {e}")
            return {"error": str(e)}
    
    async def get_currency_statistics(self, db: Session) -> Dict[str, Any]:
        """Get currency statistics."""
        try:
            total_currencies = db.query(Currency).count()
            active_currencies = db.query(Currency).filter(Currency.is_active == True).count()
            fiat_currencies = db.query(Currency).filter(
                Currency.is_active == True,
                Currency.is_crypto == False
            ).count()
            crypto_currencies = db.query(Currency).filter(
                Currency.is_active == True,
                Currency.is_crypto == True
            ).count()
            
            # Get most volatile currencies (highest rate changes)
            currencies = await self.get_all_currencies(db)
            rate_changes = []
            
            for currency in currencies:
                if currency.exchange_rate_usd > 0:
                    rate_changes.append({
                        "code": currency.code,
                        "name": currency.name,
                        "rate": currency.exchange_rate_usd,
                        "symbol": currency.symbol
                    })
            
            # Sort by rate (highest first)
            rate_changes.sort(key=lambda x: x["rate"], reverse=True)
            
            return {
                "total_currencies": total_currencies,
                "active_currencies": active_currencies,
                "fiat_currencies": fiat_currencies,
                "crypto_currencies": crypto_currencies,
                "last_update": self.last_update,
                "top_currencies_by_rate": rate_changes[:5],
                "bottom_currencies_by_rate": rate_changes[-5:]
            }
            
        except Exception as e:
            logger.error(f"Error getting currency statistics: {e}")
            return {"error": str(e)}
    
    def _is_cache_valid(self) -> bool:
        """Check if exchange rate cache is still valid."""
        if not self.last_update:
            return False
        
        return datetime.utcnow() - self.last_update < self.cache_duration
    
    async def format_salary_display(
        self, 
        amount: float, 
        currency_code: str, 
        db: Session
    ) -> str:
        """Format salary for display with proper currency symbol."""
        try:
            currency = await self.get_currency_info(currency_code, db)
            if not currency:
                return f"{amount:.2f} {currency_code}"
            
            symbol = currency.symbol or currency_code
            
            # Format based on currency
            if currency_code in ["USD", "EUR", "GBP", "CAD", "AUD", "SGD"]:
                return f"{symbol}{amount:,.2f}"
            elif currency_code in ["THB", "JPY", "CNY"]:
                return f"{symbol}{amount:,.0f}"
            else:
                return f"{amount:.2f} {symbol}"
                
        except Exception as e:
            logger.error(f"Error formatting salary: {e}")
            return f"{amount:.2f} {currency_code}" 