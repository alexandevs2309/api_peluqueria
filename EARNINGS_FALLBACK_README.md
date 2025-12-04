# Earnings API Fallback Implementation

## Overview

This implementation adds backward compatibility to the earnings API endpoints to accept `frequency` + `reference_date` parameters as a fallback while the frontend normalizes to use `year` + `fortnight` parameters directly.

## Changes Made

### 1. Helper Function (`apps/employees_api/utils.py`)

Added `date_to_year_fortnight()` function that:
- Accepts ISO date string ("YYYY-MM-DD") or date/datetime objects
- Converts to year and fortnight (1-24) where fortnight represents bi-weekly periods
- Validates input and raises ValueError for invalid dates
- Formula: `fortnight = (month - 1) * 2 + (1 if day <= 15 else 2)`

### 2. API Endpoints Modified (`apps/employees_api/earnings_views.py`)

#### GET `/api/employees/earnings/my_earnings/`
- **Before**: Required `year` and `fortnight` parameters
- **After**: Accepts either:
  - `year` + `fortnight` (existing behavior)
  - `frequency` + `reference_date` (new fallback)
- **Validation**: Only supports `frequency="fortnightly"`

#### POST `/api/employees/earnings/pay/`
- **Before**: Required `year` and `fortnight` in request body
- **After**: Accepts either:
  - `year` + `fortnight` (existing behavior)  
  - `frequency` + `reference_date` (new fallback)
- **Validation**: Only supports `frequency="fortnightly"`

### 3. Error Handling

- Invalid `reference_date` format → 400 with "Invalid reference_date format. Expected YYYY-MM-DD."
- Unsupported `frequency` → 400 with "Unsupported frequency: {value}. Only 'fortnightly' is supported."
- Missing parameters → Falls back to current fortnight

### 4. Logging

- Added `logger.debug()` statements when fallback conversion is applied
- Only logs in DEBUG mode to avoid production noise

## Testing

### Test Cases (`apps/employees_api/tests/test_earnings_api.py`)

1. **test_date_to_year_fortnight_helper()** - Tests utility function
2. **test_get_my_earnings_with_year_fortnight_preserved()** - Existing behavior works
3. **test_get_my_earnings_with_frequency_reference_date_fallback()** - New fallback works
4. **test_post_pay_with_frequency_reference_date_fallback()** - Pay endpoint fallback
5. **test_bad_reference_date_returns_400()** - Invalid date handling
6. **test_unsupported_frequency_returns_400()** - Invalid frequency handling
7. **test_fallback_produces_same_result_as_year_fortnight()** - Equivalence test

### Manual Testing

```bash
# Test GET with year/fortnight (existing)
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/employees/earnings/my_earnings/?year=2024&fortnight=24"

# Test GET with frequency/reference_date (new fallback)
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/employees/earnings/my_earnings/?frequency=fortnightly&reference_date=2024-12-20"

# Test POST with frequency/reference_date (new fallback)
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"employee_id":1,"frequency":"fortnightly","reference_date":"2024-12-20","payment_method":"cash"}' \
  "http://localhost:8000/api/employees/earnings/pay/"

# Test error cases
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/employees/earnings/my_earnings/?frequency=monthly&reference_date=2024-12-20"
```

## Backward Compatibility

- ✅ Existing `year` + `fortnight` parameters continue to work unchanged
- ✅ No breaking changes to current API consumers
- ✅ New fallback is transparent to existing code
- ✅ Same response format and structure maintained

## Future Considerations

This fallback is intended as a temporary measure while the frontend transitions to using `year` + `fortnight` parameters directly. Once the frontend is fully migrated, this fallback can be removed in a future version.

## Files Modified

- `apps/employees_api/utils.py` - Added helper function
- `apps/employees_api/earnings_views.py` - Added fallback logic
- `apps/employees_api/tests/test_earnings_api.py` - Added comprehensive tests

## Rollback Instructions

To revert these changes:
```bash
git checkout main
git branch -D fix/earnings-accept-frequency-fallback-aq
```