# Loan characteristics are hard-coded to match Table A of the pdf documentation.

import pandas as pd
import numpy as np

def calculate_mortgage_cash_flows_with_defaults(
    initial_balance=100_000_000,
    wac=8.00,
    wam=360,
    prepay_rate_smm=1.00,  # Monthly prepayment rate in percent
    default_rate_mdr=1.00,  # Monthly default rate in percent
    months_to_liquidation=12,
    loss_severity=20.00,  # Loss severity in percent
    pi_advanced=True
):
    """
    Calculate mortgage cash flows with defaults using the Standard Default Methodology.
    
    Parameters:
    -----------
    initial_balance : float
        Initial performing balance
    wac : float
        Weighted average coupon (annual %)
    wam : int
        Weighted average maturity (months)
    prepay_rate_smm : float
        Single Monthly Mortality rate (%)
    default_rate_mdr : float
        Monthly Default Rate (%)
    months_to_liquidation : int
        Time to liquidation after default
    loss_severity : float
        Loss severity (%)
    pi_advanced : bool
        Whether principal and interest are advanced
    
    Returns:
    --------
    pd.DataFrame
        DataFrame containing all cash flow calculations
    """
    
    # Initialize arrays to store results
    months = wam
    results = []
    
    # Initialize values
    perf_bal_prev = initial_balance
    fcl_prev = 0
    net_mortgage_rate = wac / 1200  # Monthly rate
    
    # Calculate scheduled amortization array
    sch_am = np.zeros(months + 1)
    c_monthly = wac / 1200
    
    for i in range(months + 1):
        remaining_months = wam - i
        if remaining_months > 0:
            bal = (1 - (1 + c_monthly)**(-remaining_months)) / \
                  (1 - (1 + c_monthly)**(-wam))
            sch_am[i] = bal * c_monthly / (1 - (1 + c_monthly)**(-wam))
        else:
            sch_am[i] = 0
    
    # Track defaults for recovery
    default_queue = []
    
    for month in range(1, months + 1):
        # Set default rate to 0 for last n months
        if month > months - months_to_liquidation:
            mdr = 0.0
        else:
            mdr = default_rate_mdr / 100
        
        smm = prepay_rate_smm / 100
        
        # New Defaults
        new_def = perf_bal_prev * mdr
        
        # Add to default queue with recovery month
        if new_def > 0:
            default_queue.append({
                'amount': new_def,
                'recovery_month': month + months_to_liquidation
            })
        
        # Amortized Default Balance in Recovery Month
        adb = 0
        for default in default_queue:
            if default['recovery_month'] == month:
                months_elapsed = month - (default['recovery_month'] - months_to_liquidation)
                if pi_advanced and month > 0 and month - 1 < len(sch_am):
                    adb += default['amount'] * (sch_am[month - 1] / sch_am[month - months_to_liquidation])
                else:
                    adb += default['amount']
        
        # Loans in Foreclosure (before removing recoveries)
        fcl = (new_def + fcl_prev - adb)
        
        # Expected Amortization
        if month > 0 and month < len(sch_am):
            amort_factor = 1 - sch_am[month] / sch_am[month - 1] if sch_am[month - 1] > 0 else 0
        else:
            amort_factor = 0
        exp_am = (perf_bal_prev + fcl_prev - adb) * amort_factor
        
        # Voluntary Prepayments
        vol_prepay = perf_bal_prev * amort_factor * smm
        
        # Amortization from Defaults
        if pi_advanced:
            am_def = (new_def + fcl_prev - adb) * amort_factor
        else:
            am_def = 0
        
        # Actual Amortization
        act_am = (perf_bal_prev - new_def) * amort_factor
        
        # Update Loans in Foreclosure (after amortization)
        fcl = fcl - am_def
        
        # Expected Interest
        exp_int = (perf_bal_prev + fcl_prev) * net_mortgage_rate
        
        # Lost Interest
        lost_int = (new_def + fcl_prev) * net_mortgage_rate
        
        # Actual Interest
        act_int = exp_int - lost_int
        
        # Principal Loss
        prin_loss = min(adb * (loss_severity / 100), adb) if adb > 0 else 0
        
        # Principal Recovery
        prin_recov = max(adb - prin_loss, 0)
        
        # Performing Balance
        perf_bal = perf_bal_prev - new_def - vol_prepay - act_am
        
        # Pool Factor
        pool_factor = perf_bal / initial_balance
        
        # Store results
        results.append({
            'Month': month,
            'Performing Balance': perf_bal,
            'New Defaults': new_def,
            'In Foreclosure': fcl,
            'Amort Factor': pool_factor,
            'Expected Amortization': exp_am,
            'Voluntary Prepayments': vol_prepay,
            'Amort From Defaults': am_def,
            'Actual Amort': act_am,
            'Expected Interest': exp_int,
            'Interest Lost': lost_int,
            'Actual Interest': act_int,
            'Principal Recovery': prin_recov,
            'Principal Loss': prin_loss,
            'In Recovery Month': adb if adb > 0 else None,
            'Default Rate': mdr,
            'Prepay Rate': smm
        })
        
        # Update for next iteration
        perf_bal_prev = perf_bal
        fcl_prev = fcl
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Format columns for display
    display_df = df.copy()
    display_df['Default Rate'] = display_df['Default Rate'] * 100
    display_df['Prepay Rate'] = display_df['Prepay Rate'] * 100
    
    return display_df

# Example usage matching Cash Flow A parameters
if __name__ == "__main__":
    df = calculate_mortgage_cash_flows_with_defaults(
        initial_balance=100_000_000,
        wac=8.00,
        wam=360,
        prepay_rate_smm=1.00,
        default_rate_mdr=1.00,
        months_to_liquidation=12,
        loss_severity=20.00,
        pi_advanced=True
    )
    
    # Set display options to show all rows
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', lambda x: f'{x:,.2f}')
    
    print("Cash Flow A Replication - Complete 360 Month Schedule")
    print("=" * 150)
    print(f"\nParameters:")
    print(f"  Initial Balance: ${df.iloc[0]['Performing Balance'] + df.iloc[0]['New Defaults'] + df.iloc[0]['Voluntary Prepayments'] + df.iloc[0]['Actual Amort']:,.2f}")
    print(f"  WAC: 8.00%")
    print(f"  WAM: 360 months")
    print(f"  Prepay Rate: 1% SMM")
    print(f"  Default Rate: 1% MDR")
    print(f"  Recovery Time: 12 months")
    print(f"  Loss Severity: 20.00%")
    print(f"  P&I Advanced: Yes\n")
    
    # Display all 360 months
    print(df.to_string(index=False))
    
    # Calculate totals
    print("\n" + "=" * 150)
    print("TOTALS:")
    print(f"  Total New Defaults:           {df['New Defaults'].sum():>20,.2f}")
    print(f"  Total Voluntary Prepayments:  {df['Voluntary Prepayments'].sum():>20,.2f}")
    print(f"  Total Actual Amortization:    {df['Actual Amort'].sum():>20,.2f}")
    print(f"  Total Expected Interest:      {df['Expected Interest'].sum():>20,.2f}")
    print(f"  Total Interest Lost:          {df['Interest Lost'].sum():>20,.2f}")
    print(f"  Total Actual Interest:        {df['Actual Interest'].sum():>20,.2f}")
    print(f"  Total Principal Recovery:     {df['Principal Recovery'].sum():>20,.2f}")
    print(f"  Total Principal Loss:         {df['Principal Loss'].sum():>20,.2f}")
    print(f"\n  Final Performing Balance:     {df.iloc[-1]['Performing Balance']:>20,.2f}")
    
    # Save to CSV for easier viewing
    df.to_csv('cash_flow_a_replication.csv', index=False)
    print(f"\n  Data also saved to 'cash_flow_a_replication.csv'")
