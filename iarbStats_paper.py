import IndexArbitrage.cfg as cfg

mode = 'paper'

if mode == 'live':
    import IndexArbitrage.cfg_live as cfg_i_arb
elif mode == 'paper':
    import IndexArbitrage.cfg as cfg_i_arb



import utils.log as lg
lg.LOG_FILE = cfg_i_arb.LOG_FILE
logger = lg.get_logger(__name__)

import streamlit as st
from utils import sleep, datetime, timedelta, pd, np, beep, read_dict, getNextMarketOpen, \
	timezone, \
    plt
from uIbapi.ManageOrders import manageOrders, barSize
import IndexArbitrage.funcs as fc
from IndexArbitrage.cat import Position, searchResultMap, positionMap



st.set_page_config(layout="wide")

plt.style.use('dark_background')

TOL_LAST_CHECK_WITH_PORTFOLIO = 300
TOL_LAST_CHECK_NO_PORTFOLIO = 600
DELAY = .5

lastHealthCheckOk = datetime.now()
c_live_sign = 'green'
dt_market_open, dt_market_close = getNextMarketOpen()
tz = timezone('America/Sao_Paulo')
dt_market_open, dt_market_close = dt_market_open.astimezone(tz).replace(
      tzinfo=None) + cfg_i_arb.WAIT_TILL + timedelta(seconds=120), dt_market_close.astimezone(
    tz).replace(tzinfo=None) + cfg_i_arb.RUN_TILL

def calcPNL(parms):
    di_pm = diPaper[parms]
    dfStrategies = mo._readStrategiesTable(tableName=diTables['strategies']['table'])
    symbols = dfStrategies.symbol.to_list()
    dfClose = mm.sql_read_col_table(symbols=symbols, wts=di_pm['wts'],
                                    BarSizeStr=di_pm['BarSizeStr'],
                                    dtStart=datetime.now() - barSize.q_BarSizeStr_to_Timedelta(
                                          di_pm['BarSizeStr']) * 3).fillna(method='pad')
    dfStrategies['current'] = dfStrategies.ExecutedQuantity * dfClose.iloc[-1][
        dfStrategies.symbol].values
    dfStrategies['buyPrice'] = dfStrategies.ExecutedQuantity * dfStrategies.OpenPrice

    return (dfStrategies['current'] - dfStrategies['buyPrice']).sum()

def styleMap(v):
    if v == 'NOT OK':
        return 'background: darkred'
    elif v == 'none':
        return 'color: green'
    elif v in ['long', 'short']:
        return 'color: yellow'
    elif pd.isna(v):
        return 'color: black'
    else:
        return 'color: white'

def backColor(x, cols):
    return ['background: red' if s in cols else '' for s in x.index]

def highlight_vals(row):
    styles = {col: '' for col in row.index}
    col = 'dist'
    if row[col] > -0.5:
        styles[col] = 'color: lightgreen'
    elif row[col] >= -1.7:
        styles[col] = 'color: yellow'
    elif row[col] < -1.7:
        styles[col] = 'color: red'

    col = 'lastCheck'
    if row[col] > 60:
        styles[col] = 'color: darkred'
    elif row[col] >= 15:
        styles[col] = 'color: darkyellow'
    elif row[col] < 15:
        styles[col] = 'color: lightgreen'

    if 'PnL' in row.keys():
        col = 'PnL'
        if row[col] is None:
            pass
        elif row[col] > 0:
            styles[col] = 'background-color: darkgreen'
        elif row[col] < 0:
            styles[col] = 'background-color: darkred'

    return styles

def healthCheck():
    """ check health stats to see if everything is running and beeps if not"""
    global lastHealthCheckOk, dfOpenTrades, dfWithPortfolios, dfPrcsStats, lastHealthOkElapsed

    idx = ['iArbPrcs', 'calcPrcs', 'mktInfoPrcs']
    if cfg_i_arb.START_HISTORY:
        idx +=['historyPrcs']
    fHCchekOk = (dfPrcsStats.loc[idx, 'Alive'] == dfPrcsStats.loc[idx, 'Total']).all()

    if (dfIArbStats['position'] != 'none').any():  # has open trades
        fHCchekOk *= not pd.isna(dfOpenTrades.loc[:, ['zLong', 'zShort']].values).any()
        fHCchekOk *= (dfOpenTrades.loc[:, 'dataTimeOk'].values == 'OK').all()

    if (dfIArbStats['portfolios'] != 0).any():  # has portfolios
        fHCchekOk *= (not pd.isna(dfWithPortfolios.loc[:, ['zLong',
                                                           'zShort']].values).any())  # fHCchekOk
        # *= (dfWithPortfolios.loc[:, 'dataTimeOk'].values == 'OK').all()

    if fHCchekOk:
        lastHealthCheckOk = datetime.now()
    lastHealthOkElapsed = max((datetime.now() - lastHealthCheckOk).seconds, min_last_check)

    # alert ?
    if ((lastHealthOkElapsed > TOL_LAST_CHECK_WITH_PORTFOLIO and (
          (dfIArbStats['position'] != 'none').any() or (dfIArbStats['portfolios'] != 0).any())) or (
              lastHealthOkElapsed > TOL_LAST_CHECK_NO_PORTFOLIO)) and playSound and \
	    dt_market_open <= datetime.now() <= dt_market_close:
        beep(1000, 500)

def show_trades():
    global dfstrategiesAll, tradeId
    dfstrategiesAll = db.select(table=diTables['strategies']['table'],
                                db=diTables['strategies']['db']).set_index('id')
    dfLogTrades = db.df_from_sql(table=diTables['logTrades']['table'],
                                 db=diTables['logTrades']['db'])
    dfLogTrades = dfLogTrades[dfLogTrades.id >= 86].set_index('id')
    if cfg_i_arb.MODE == 'paper':
        dfLogTrades.drop(
          list(range(87, 95)) + [100, 101] + list(range(120, 153)) + list(range(154, 158)),
          inplace=True)
    dfLogTrades.insert(0, 'Strategy', dfLogTrades.apply(
        lambda x: dfstrategiesAll.set_index('StrategyId').at[x.name, 'Strategy'].values[
            0] if x.name in dfstrategiesAll['StrategyId'].values else '', axis=1))
    tradeId = st.selectbox('Select trade', dfLogTrades.index[::-1])
    cols = dfLogTrades.columns.to_list()
    cols = cols[:2] + cols[-5:] + cols[2:-5]
    st.dataframe(
          dfLogTrades.loc[dfLogTrades.index[::-1], cols].style.set_precision(2).highlight_min(
              subset=['resultPerc', 'gross', 'pnl', 'assets'], color='blue').highlight_max(
                subset=['resultPerc', 'gross', 'pnl', 'assets'], color='green').apply(
                lambda x: ['background: darkgreen' if x.name == tradeId else '' for i in x],
                axis=1).format({
                'resultPerc': lambda x: f'{x:,.3%}', 'gross': lambda x: f'{x:,.0f}',
                'pnl':        lambda x: f'{x:,.2f}',
                'dtStart':    lambda x: f'{x:%d-%b}' if not pd.isna(x) else '',
                'dtEnd':      lambda x: f'{x:%d-%b}' if not pd.isna(x) else ''
          }))
    resultPerc = dfLogTrades["resultPerc"].dropna().values
    if len(resultPerc):
        st.sidebar.text(f'trades: {len(resultPerc)}, positive: {(resultPerc >= 0).sum()}, '
                    f'negative: {(resultPerc < 0).sum()}\n'
                    f'% positive: {(resultPerc >= 0).sum() / len(resultPerc):,.0%}, '
                    f'avg res: {resultPerc[resultPerc >= 0].mean():.3%}\n'
                    f'% negative: {(resultPerc < 0).sum() / len(resultPerc):,.0%}, '
                    f'avg res: {resultPerc[resultPerc < 0].mean():.3%}\n'
                    f'net cash: {dfLogTrades["pnl"].sum():,.2f}\n'
                    f'total result: {dfLogTrades["resultPerc"].sum():,.3%}, '
                    f'{dfLogTrades["resultPerc"].sum() / len(dfLogTrades):,.3%}/trade')
    dfstrategies = dfstrategiesAll[dfstrategiesAll['StrategyId'] == tradeId]
    st.dataframe(dfstrategies, 2500, 1000)
    plotBktst = st.sidebar.button('plot backtest')
    if plotBktst:
        fig = fc.plot_bk_tsts_results(Parms=dfstrategies.Strategy.values[0][5:], returnFig=True)
        the_plot = st.pyplot(fig=fig)
    plotTrade = st.sidebar.button('plot trade')
    if plotTrade:
        fig = fc.calc_and_plot_live_trade(tradeId, plotTrade=True, returnFig=True)
        the_plot = st.pyplot(fig=fig)
    showStats = st.sidebar.button('show stats')
    if showStats:
        msg = fc.calc_iarb_live_results_by_strategy_and_barsize()
        st.text(msg)

def show_live():
    global dfPrcsStats, dfIArbStats, dfOpenTrades, dfWithPortfolios, min_last_check, c_live_sign
    while True:
        dfPrcsStats = db.df_from_sql(table=diTables['dfPrcsStats']['table'],
                                     db=diTables['dfPrcsStats']['db'])
        dfIArbStats = db.df_from_sql(table=diTables['dfIArbStats']['table'],
                                     db=diTables['dfIArbStats']['db'])
        dfIArbStats.sort_values(by=['position', 'portfolios', 'wait', 'parms'],
                                ascending=[False, False, True, True], inplace=True)
        dfIArbStats['searchResult'] = dfIArbStats['searchResult'].map(searchResultMap)
        dfIArbStats['dataTimeOk'] = dfIArbStats['dataTimeOk'].map({0: 'NOT OK', 1: 'OK'})
        dfIArbStats['position'] = dfIArbStats['position'].map(positionMap)
        dfIArbStats['lastCheck'] = (
                  datetime.now() - pd.to_datetime(dfIArbStats['lastCheck']).dt.tz_localize(
                None)).dt.total_seconds()
        dfIArbStats['wait'] = dfIArbStats.apply(
            lambda x: (x.wait - datetime.now()).seconds if x.wait > datetime.now() else 0, axis=1)
        dfIArbStats.set_index('parms', inplace=True)
        dfPrcsStats.set_index('processes', inplace=True)
        dfIArbStats['zLong'] = pd.to_numeric(dfIArbStats['zLong'], errors='coerce')
        dfIArbStats['zHist'] = pd.to_numeric(dfIArbStats['zHist'], errors='coerce')
        dfIArbStats['zShort'] = pd.to_numeric(dfIArbStats['zShort'], errors='coerce')
        dfIArbStats.insert(0, 'dist', -dfIArbStats.apply(
              lambda x: x.zLong - x.exit if x.position == positionMap[
                  Position.short] else -x.zShort - x.exit if x.position == positionMap[
                  Position.long] else min(x.entry + x.zLong,
                                          x.entry - x.zShort) if x.portfolios != 0 else np.nan,
              axis=1))

        dfIArbStats.loc[dfIArbStats[(dfIArbStats['dataTimeOk'] == 'NOT OK') | (
              pd.isna(dfIArbStats['searchResult']))].index, 'searchResult'] = ''

        dfOpenTrades = dfIArbStats[dfIArbStats['position'] != positionMap[Position.none]][colsOT]
        dfOpenTrades.insert(3, 'PnLperc', dfOpenTrades['PnL'] / dfOpenTrades['gross'])
        dfWithPortfolios = dfIArbStats[(dfIArbStats['position'] == positionMap[Position.none]) & (
              dfIArbStats['portfolios'] > 0)][colsWP]
        dfNoPortfolios = dfIArbStats[(dfIArbStats['position'] == positionMap[Position.none]) & (
              dfIArbStats['portfolios'] == 0)][colsNP]

        if len((dfOpenTrades)) > 0:
            tiOT.text(f'Open Trades ({len(dfOpenTrades)})')
            tOT.dataframe(dfOpenTrades.style.bar(subset='dist', vmin=0, vmax=-2.2,
                                                 color=['darkgreen', 'darkgreen'], width=100,
                                                 align='left').applymap(styleMap).apply(
                lambda x: highlight_vals(x), axis=1).set_properties(**{'height': '10'}).format(
                  dict(lastCheck=lambda x: f'{x:,.0f}', id=lambda x: f'{x:,.0f}' if x > 0 else '',
                       dist=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       PnL=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       PnLperc=lambda x: f'{x:,.2%}' if not pd.isna(x) else '',
                       gross=lambda x: f'{x:,.0f}' if not pd.isna(x) else '',
                       zLong=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       zShort=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       zHist=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       assets=lambda x: f'{x:,.0f}' if x else '')))
        else:
            tiOT.text('')
            tOT.text('')

        if len((dfWithPortfolios)) > 0:
            tiWP.text(f'Found portfolios ({len(dfWithPortfolios)})')
            tWP.dataframe(dfWithPortfolios.style.bar(subset='dist', vmin=0, vmax=-2.2,
                                                     color=['darkgreen', 'darkgreen'], width=100,
                                                     align='left').applymap(styleMap).apply(
                lambda x: highlight_vals(x), axis=1).set_properties(**{'height': '10'}).format(
                  dict(lastCheck=lambda x: f'{x:,.0f}',
                       dist=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       zLong=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       zShort=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       zHist=lambda x: f'{x:,.2f}' if not pd.isna(x) else '',
                       portfolios=lambda x: f'{x:,.0f}' if x else '')).set_precision(2))
        else:
            tWP.text('')
            tiWP.text('')
        if len(dfNoPortfolios):
            tiNP.text(f'Searching for portfolios ({len(dfNoPortfolios)})')
            tNP.dataframe(dfNoPortfolios.style.highlight_min(subset=['wait', 'lastCheck'],
                                                             color='darkblue').highlight_max(
                  subset=['wait', 'lastCheck'], color='darkgreen').set_properties(
                  **{'height': '10'}).format(dict(lastCheck=lambda x: f'{x:,.0f}', )).set_precision(
                2), 2000, 1000)
        else:
            tiNP.text('')
            tNP.text('')
        tPrcsStats.dataframe(dfPrcsStats[['Alive', 'Total']])
        min_last_check = min(dfIArbStats["lastCheck"])
        healthCheck()
        dataOK = sum(dfIArbStats["dataTimeOk"] == "OK")
        l_data = len(dfIArbStats)
        c_live_sign = 'green' if c_live_sign == 'yellow' else 'yellow'
        msg = f'<p style="font-family:sans-serif; color:White; font-size: 15px;">' \
              f' <span style="background: {c_live_sign}; color: {c_live_sign}">A</span><br> ' \
              f' <span style="background: ' \
              f'{"red" if lastHealthOkElapsed > 60 else "darkyellow" if lastHealthOkElapsed > 15 else "green"}">' \
              f'Last Check:' \
              f' {lastHealthOkElapsed:,.0f} s</span><br>' \
              f' <span style="background: ' \
              f'{"green" if dataOK / l_data == 1 else "red"}">'\
              f'Data OK: {dataOK}/{l_data} ({dataOK / l_data:,.0%})</span><br><br>'
        try:
            msg += f'Gross On Trade: $ {sum(dfOpenTrades["gross"]):,.0f}<br>' \
                  f'PnL: $ {sum(dfOpenTrades["PnL"]):,.2f}<br>' \
                  f'PnL %: {sum(dfOpenTrades["PnL"]) / sum(dfOpenTrades["gross"]):,.4%}<br><br>'
        except:
            pass
        for k in positionMap.keys():
            v = sum(dfIArbStats["position"] == positionMap[k])
            if v:
                msg += f'{positionMap[k]}: {v}<br>'
        msg += f'Portfolios: {dfIArbStats["portfolios"].sum()}<br>'
        msg += '</p>'
        tLastCheck.markdown(msg, unsafe_allow_html=True)
        sleep(DELAY)

if __name__ == '__main__':
    diTables = cfg_i_arb.SQL_TABLES

    diPaper = read_dict(cfg_i_arb.FILE_PARMS, add='')
    mo = manageOrders(Path=cfg_i_arb.PATH, db_to_use=cfg_i_arb.DB_TO_USE)
    db = mo.db
    mm = mo.mm

    tLastCheck = st.sidebar.text(' ')
    tiOT = st.text('')
    tOT = st.text('')
    tiWP = st.text('')
    tWP = st.text('')
    tiNP = st.text('')
    tNP = st.text('')

    playSound = st.sidebar.checkbox('Beep', value=True)
    testBeep = st.sidebar.button('beep test')

    if testBeep:
        beep(1000, 500)
    tPrcsStats = st.sidebar.dataframe(pd.DataFrame())

    show_trades()

    colsOT = ['dist', 'dataTimeOk', 'lastCheck', 'position', 'PnL', 'gross', 'zLong', 'zShort',
              'zHist', 'assets', 'id', 'exit']
    colsWP = ['dist', 'dataTimeOk', 'lastCheck', 'zLong', 'zShort', 'zHist', 'portfolios', 'entry',
              'exit']
    colsNP = ['searchResult', 'lastCheck', 'wait', 'dataTimeOk']

    show_live()