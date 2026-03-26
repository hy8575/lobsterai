# A股数据字典 (a_share.db)

本文件由脚本自动生成，供 Cursor Agent 因子提取时参考。
仅使用下列已有字段，禁止编造不存在的字段名。

---

## adj_factor
ts_code, trade_date, adj_factor

## daily_basic (日线基本面)
ts_code, trade_date, close, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv

## daily_unadj (日线行情-不复权)
ts_code, trade_date, open, close, high, low, vol, amount, amplitude, pct_chg, change, turnover

## fin_balance (资产负债表)
ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, total_assets, total_liab, total_hldr_eqy_exc_min_int, money_cap, inventories, accounts_receiv, fixed_assets, total_cur_assets, total_cur_liab, update_flag

## fin_cashflow (现金流量表)
ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, n_cashflow_act, c_inf_fr_operate_a, st_cash_out_act, n_cashflow_inv_act, n_cash_flows_fnc_act, free_cashflow, c_cash_equ_end_period, update_flag

## fin_income (利润表)
ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, total_revenue, revenue, oper_cost, operate_profit, total_profit, n_income, n_income_attr_p, basic_eps, diluted_eps, update_flag

## fin_indicator (财务指标)
ts_code, ann_date, end_date, eps, dt_eps, total_revenue_ps, revenue_ps, capital_rese_ps, surplus_rese_ps, undist_profit_ps, extra_item, profit_dedt, gross_margin, current_ratio, quick_ratio, cash_ratio, invturn_days, arturn_days, inv_turn, ar_turn, ca_turn, fa_turn, assets_turn, op_income, valuechange_income, interst_income, daa, ebit, ebitda, fcff, fcfe, current_exint, noncurrent_exint, interestdebt, netdebt, tangible_asset, working_capital, networking_capital, invest_capital, retained_earnings, diluted2_eps, bps, ocfps, retainedps, cfps, ebit_ps, fcff_ps, fcfe_ps, netprofit_margin, grossprofit_margin, cogs_of_sales, expense_of_sales, profit_to_gr, saleexp_to_gr, adminexp_of_gr, finaexp_of_gr, impai_ttm, gc_of_gr, op_of_gr, ebit_of_gr, roe, roe_waa, roe_dt, roa, npta, roic, roe_yearly, roa2_yearly, roe_avg, opincome_of_ebt, investincome_of_ebt, n_op_profit_of_ebt, tax_to_ebt, dtprofit_to_profit, salescash_to_or, ocf_to_or, ocf_to_opincome, capitalized_to_da, debt_to_assets, assets_to_eqt, dp_assets_to_eqt, ca_to_assets, nca_to_assets, tbassets_to_totalassets, int_to_talcap, eqt_to_talcapital, currentdebt_to_debt, longdeb_to_debt, ocf_to_shortdebt, debt_to_eqt, eqt_to_debt, eqt_to_interestdebt, tangibleasset_to_debt, tangasset_to_intdebt, tangibleasset_to_netdebt, ocf_to_debt, ocf_to_interestdebt, ocf_to_netdebt, ebit_to_interest, longdebt_to_workingcapital, ebitda_to_debt, turn_days, roa_yearly, roa_dp, fixed_assets, profit_to_op, q_opincome, q_investincome, q_dtprofit, q_eps, q_netprofit_margin, q_gsprofit_margin, q_exp_to_sales, q_profit_to_gr, q_saleexp_to_gr, q_adminexp_to_gr, q_finaexp_to_gr, q_impair_to_gr_ttm, q_gc_to_gr, q_op_to_gr, q_roe, q_dt_roe, q_npta, q_opincome_to_ebt, q_investincome_to_ebt, q_dtprofit_to_profit, q_salescash_to_or, q_ocf_to_sales, q_ocf_to_or, basic_eps_yoy, dt_eps_yoy, cfps_yoy, op_yoy, ebt_yoy, netprofit_yoy, dt_netprofit_yoy, ocf_yoy, roe_yoy, bps_yoy, assets_yoy, eqt_yoy, tr_yoy, or_yoy, q_gr_yoy, q_gr_qoq, q_sales_yoy, q_sales_qoq, q_op_yoy, q_op_qoq, q_profit_yoy, q_profit_qoq, q_netprofit_yoy, q_netprofit_qoq, equity_yoy, rd_exp, update_flag

## stock_list (股票列表)
ts_code, symbol, name, area, industry, fullname, enname, cnspell, market, exchange, list_date, chairman, chairman_type, is_delisted, delist_date

## limit_price (涨跌停)
ts_code, trade_date, pre_close, up_limit, down_limit

## st_status (ST状态)
ts_code, trade_date, name, st_type, st_type_name

## suspension (停牌)
ts_code, trade_date, time_range, suspend_type

## index_daily (指数行情)
ts_code, trade_date, name, open, close, high, low, vol, amount, up_count, down_count

## index_list (指数列表)
ts_code, name, market, publisher, category, base_date, base_point, list_date

## monthly_unadj (月线-不复权)
ts_code, trade_date, open, close, high, low, vol, amount, amplitude, pct_chg, change, turnover

## weekly_unadj (周线-不复权)
ts_code, trade_date, open, close, high, low, vol, amount, amplitude, pct_chg, change, turnover