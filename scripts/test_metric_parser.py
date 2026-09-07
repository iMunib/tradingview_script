import asyncio
import json
import re
import websockets
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner

async def main():
    ws_url = runner.get_ws_url()
    client = runner.CDPClient(ws_url)
    await client.connect()
    await client.find_tradingview_target()
    js_code = """
    (() => {
        const report = document.querySelector('[class*="reportContainer-"]') || 
                       document.querySelector('[class*="wrapper-dmId9qUc"]') ||
                       document.querySelector('[class*="wrapper-yprR2JgA"]');
        if (!report) return { error: 'No report container found' };
        const text = report.innerText;
        return { raw: text };
    })()
    """
    res = await client.eval_js(js_code)
    raw_text = res.get('raw', '')
    await client.close()

    print("Raw text to parse:\n", raw_text)
    
    # Parse metrics
    metrics = {}
    
    # Net Profit / Total PnL
    m_pnl = re.search(r'Total PnL\s*\n?([+\-−]?[0-9,.]+(?:USD|\$|EUR)?[+\-−]?[0-9,.]+\s*%)', raw_text)
    if m_pnl:
        metrics['net_profit'] = m_pnl.group(1).strip()
    
    # Max Drawdown
    m_dd = re.search(r'Max drawdown\s*\n?([0-9,.]+(?:USD|\$|EUR)?[0-9,.]+\s*%)', raw_text)
    if m_dd:
        metrics['max_drawdown'] = m_dd.group(1).strip()
        
    # Profitable Trades / Win Rate & Closed Trades
    m_win = re.search(r'Profitable trades\s*\n?([0-9,.]+\s*%)\s*([0-9]+)\s*/\s*([0-9]+)', raw_text)
    if m_win:
        metrics['win_rate'] = m_win.group(1).strip()
        metrics['winning_trades'] = int(m_win.group(2))
        metrics['total_closed_trades'] = int(m_win.group(3))
        
    # Profit Factor
    m_pf = re.search(r'Profit factor\s*\n?([0-9,.]+)', raw_text)
    if m_pf:
        metrics['profit_factor'] = float(m_pf.group(1).replace(',', ''))
        
    print("\nParsed metrics:\n", json.dumps(metrics, indent=2))

asyncio.run(main())
