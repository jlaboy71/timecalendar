# Year-End Processing

Year-end processing is an **automatic system** that prepares PTO Central for each new calendar year. It runs once per year, triggered by the first user login after January 1st.

## What Year-End Processing Does

1. **Creates PTO Balances**
   - Every active employee receives their annual PTO allocation
   - Vacation based on years of service:
     - 0-4 years: 10 vacation days
     - 5-9 years: 15 vacation days
     - 10+ years: 20 vacation days
   - Plus: 5 sick days and 2 personal days for everyone

2. **Applies Carryover Requests (Sick Time Only)**
   - Approved sick time carryover requests are applied
   - Sick time can roll over up to 56-80 hours depending on location
   - Vacation and personal days are "use it or lose it" - no carryover

3. **Generates Market Holidays**
   - Federal and exchange holidays (NYSE, CME, CBOE) are automatically calculated
   - Includes: New Year, MLK Day, Presidents Day, Good Friday, Memorial Day, Juneteenth, July 4th, Labor Day, Thanksgiving, Christmas

## When Does It Run?

- **Trigger**: First login by any user on or after January 1st of the new year
- **Duration**: Usually completes in a few seconds
- **Frequency**: Once per year (the system tracks if it has already run)
- **No action required**: This is fully automatic - you don't need to do anything

## Viewing Year-End Status

Navigate to **Admin** > **Year-End Status** to see:
- Whether current year processing is complete
- Processing results (balances created, carryovers applied, holidays generated)
- Countdown to next year's processing
- Any pending carryover requests that need attention

## Pre-Year-End Checklist

Before the new year:
- Review and approve/deny all pending carryover requests
- Remind employees to use vacation before it expires
- Verify employee records are up to date

## Troubleshooting

**Processing Not Showing Complete:**
- Wait for first login of the new year
- Check the Year-End Status page for details

**Missing Balances:**
- New employees added after year-end processing automatically get their PTO balance created
- Check if the employee is marked as active

## Best Practices

- Process carryover requests before year-end
- Review Year-End Status page after January 1st to confirm processing
- Market holidays can be synced manually in System Administration if needed
