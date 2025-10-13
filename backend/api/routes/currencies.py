from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from api.models.database import get_db, User
from api.models.schemas import CurrencyResponse, CurrencyUpdate, SalaryConversionRequest, SalaryConversionResponse
from api.routes.auth import get_current_user
from api.services.currency_service import CurrencyService

router = APIRouter()
currency_service = CurrencyService()

@router.get("/", response_model=List[CurrencyResponse])
async def get_all_currencies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active currencies."""
    try:
        currencies = await currency_service.get_all_currencies(db)
        return currencies
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving currencies: {str(e)}"
        )

@router.get("/fiat", response_model=List[CurrencyResponse])
async def get_fiat_currencies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all fiat currencies."""
    try:
        currencies = await currency_service.get_fiat_currencies(db)
        return currencies
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving fiat currencies: {str(e)}"
        )

@router.get("/crypto", response_model=List[CurrencyResponse])
async def get_crypto_currencies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all cryptocurrency currencies."""
    try:
        currencies = await currency_service.get_crypto_currencies(db)
        return currencies
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving crypto currencies: {str(e)}"
        )

@router.get("/{currency_code}", response_model=CurrencyResponse)
async def get_currency_info(
    currency_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get information about a specific currency."""
    try:
        currency = await currency_service.get_currency_info(currency_code, db)
        if not currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Currency not found"
            )
        
        return currency
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving currency info: {str(e)}"
        )

@router.post("/convert", response_model=SalaryConversionResponse)
async def convert_salary(
    conversion_request: SalaryConversionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert salary between currencies."""
    try:
        conversion_result = await currency_service.convert_salary(conversion_request, db)
        
        if "error" in conversion_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=conversion_result["error"]
            )
        
        return conversion_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting salary: {str(e)}"
        )

@router.post("/convert-range")
async def convert_salary_range(
    min_salary: float,
    max_salary: float,
    from_currency: str,
    to_currency: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert salary range between currencies."""
    try:
        conversion_result = await currency_service.get_salary_range_conversion(
            min_salary=min_salary,
            max_salary=max_salary,
            from_currency=from_currency,
            to_currency=to_currency,
            db=db
        )
        
        if "error" in conversion_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=conversion_result["error"]
            )
        
        return conversion_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting salary range: {str(e)}"
        )

@router.post("/update-rates")
async def update_exchange_rates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update exchange rates from external APIs."""
    if current_user.role not in ["government", "consultant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only government and consultant users can update exchange rates"
        )
    
    try:
        rates = await currency_service.update_exchange_rates(db)
        return {
            "message": "Exchange rates updated successfully",
            "currencies_updated": len(rates),
            "rates": rates
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating exchange rates: {str(e)}"
        )

@router.put("/{currency_code}", response_model=CurrencyResponse)
async def update_currency(
    currency_code: str,
    update_data: CurrencyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update currency information (admin only)."""
    if current_user.role not in ["government", "consultant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only government and consultant users can update currencies"
        )
    
    try:
        currency = await currency_service.update_currency(currency_code, update_data, db)
        if not currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Currency not found"
            )
        
        return currency
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating currency: {str(e)}"
        )

@router.get("/statistics/overview")
async def get_currency_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get currency statistics."""
    try:
        statistics = await currency_service.get_currency_statistics(db)
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving currency statistics: {str(e)}"
        )

@router.post("/initialize")
async def initialize_currencies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize supported currencies in the database."""
    if current_user.role not in ["government", "consultant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only government and consultant users can initialize currencies"
        )
    
    try:
        currencies = await currency_service.initialize_currencies(db)
        return {
            "message": "Currencies initialized successfully",
            "currencies_created": len(currencies)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing currencies: {str(e)}"
        )

@router.post("/format-salary")
async def format_salary_display(
    amount: float,
    currency_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Format salary for display with proper currency symbol."""
    try:
        formatted_salary = await currency_service.format_salary_display(amount, currency_code, db)
        return {
            "amount": amount,
            "currency_code": currency_code,
            "formatted_display": formatted_salary
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error formatting salary: {str(e)}"
        )

@router.get("/supported/list")
async def get_supported_currencies():
    """Get list of all supported currencies."""
    return {
        "fiat_currencies": [
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
            {"code": "THB", "name": "Thai Baht", "symbol": "฿"},
            {"code": "GBP", "name": "British Pound", "symbol": "£"},
            {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
            {"code": "SGD", "name": "Singapore Dollar", "symbol": "S$"},
            {"code": "AUD", "name": "Australian Dollar", "symbol": "A$"},
            {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$"},
            {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF"},
            {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥"}
        ],
        "crypto_currencies": [
            {"code": "BTC", "name": "Bitcoin", "symbol": "₿"},
            {"code": "ETH", "name": "Ethereum", "symbol": "Ξ"},
            {"code": "USDT", "name": "Tether", "symbol": "₮"},
            {"code": "BNB", "name": "Binance Coin", "symbol": "BNB"},
            {"code": "3DOT", "name": "3DOT Token", "symbol": "3DOT"},
            {"code": "ARHC", "name": "ARHC Token", "symbol": "ARHC"}
        ]
    }

@router.get("/exchange-rates/current")
async def get_current_exchange_rates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current exchange rates for all currencies."""
    try:
        currencies = await currency_service.get_all_currencies(db)
        rates = {}
        
        for currency in currencies:
            rates[currency.code] = {
                "name": currency.name,
                "symbol": currency.symbol,
                "rate_usd": currency.exchange_rate_usd,
                "is_crypto": currency.is_crypto,
                "last_updated": currency.updated_at
            }
        
        return {
            "rates": rates,
            "total_currencies": len(rates),
            "last_update": currency_service.last_update
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving exchange rates: {str(e)}"
        )

@router.post("/bulk-convert")
async def bulk_convert_salaries(
    conversions: List[SalaryConversionRequest],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert multiple salaries at once."""
    try:
        results = []
        for conversion in conversions:
            result = await currency_service.convert_salary(conversion, db)
            results.append(result)
        
        return {
            "conversions": results,
            "total_conversions": len(results)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing bulk conversion: {str(e)}"
        ) 