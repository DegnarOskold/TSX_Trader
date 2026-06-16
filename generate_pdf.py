from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Automated TSX Trading System Overview', border=False, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_pdf():
    pdf = PDF()
    
    # ---------------- PAGE 1 ----------------
    page_1 = """
1. Introduction: Building an Automated Trading Advisor

Managing a stock portfolio actively takes a lot of time. You have to constantly check stock prices, read financial news, and keep a detailed record of what you bought and sold to understand your true profit. It is easy to miss important information or make decisions based on emotion rather than data.

To solve this, we built a fully automated trading advisor. 

Think of this system as a tireless junior analyst. It lives on your computer and operates completely in the background. Its job is to ingest live market data, read the latest financial news, and use modern Artificial Intelligence (AI) to make sense of it all. It then sends you a concise, data-driven recommendation on whether you should buy, sell, or hold your positions.

This document breaks down exactly how the system works. We will look at how it tracks the hard numbers (Quantitative data), how it reads the news (Qualitative data), how the AI makes its decisions, and how it communicates with you seamlessly through the Telegram messaging app.
"""

    # ---------------- PAGE 2 ----------------
    page_2 = """
2. The Quantitative Side: Tracking the Numbers

Every good trading decision starts with the math. Before the system even looks at the news, it builds a strict mathematical and technical profile of your portfolio.

Live Market Polling & Technical Momentum
Every hour, the system securely connects to Yahoo Finance. It pulls the exact, live trading prices for your specific stocks - in this case, Canadian Natural Resources (CNQ.TO) and Barrick Gold (ABX.TO). It tracks trading volume, but also calculates advanced technical indicators on the fly: the 14-day Relative Strength Index (RSI) and the 50-day Simple Moving Average (SMA). 

These momentum indicators tell the AI if a stock is mathematically "overbought" or "oversold," or if it is breaking critical historical support lines.

Dynamic Ledger & Cash Constraints
Knowing the current price of a stock is only helpful if you know what you originally paid for it. The system maintains a private, automated CSV ledger that records every trade you make. 

Using this ledger, the system constantly calculates your Adjusted Cost Base (ACB). It also tracks your exact Available Free Cash. The AI operates under strict instructions: it will never recommend a BUY action if your ledger shows insufficient free cash to execute the trade, protecting you from over-leveraging.
"""

    # ---------------- PAGE 3 ----------------
    page_3 = """
3. The Qualitative Side: Understanding Micro News

While the numbers tell us what a stock is worth right now, the news tells us where the stock might be heading tomorrow. This is called Qualitative Analysis. The system specifically targets and pulls the 10 most recent news headlines for each individual asset in your portfolio. We call this "Micro News."

Dynamic & Sector-Agnostic Feeds
The system is completely sector-agnostic. Instead of hardcoding specific stocks, it reads your portfolio configuration and dynamically fetches the exact RSS feeds required for your holdings. 

For example, the system will pick up on headlines about a new earnings report, a change in leadership, or an analyst upgrading a stock's rating. These qualitative metrics are crucial. A stock's price might be dropping today, but if the system reads a headline about a massive new contract, it knows the long-term outlook is positive.
"""

    # ---------------- PAGE 4 ----------------
    page_4 = """
4. The Qualitative Side: Understanding Macro News

Looking only at company-specific news is not enough. Stocks do not exist in a vacuum; they are heavily influenced by the broader global economy. To capture this, the system allows you to pair Macro topics with your stock holdings.

Global Events and Sentiment
The system monitors these broader topics to understand global market sentiment. 

For example, if you hold an energy stock, you can configure the system to also pull WTI Crude Oil headlines. When the system reads headlines about geopolitical tensions, it understands the underlying economic metric: global oil supply is threatened.

The AI connects these dots. It recognizes that even if your specific company hasn't released news today, the broader Macro environment is highly bullish. This global qualitative data is often the strongest indicator of how an asset will perform in the coming days.
"""

    # ---------------- PAGE 5 ----------------
    page_5 = """
5. The Synthesis: How the AI Makes Decisions

With all the numbers (Quantitative) and the news (Qualitative) gathered, the system must now make a decision. To do this, it packages all this data into a "Dossier" and hands it to a Large Language Model (LLM) - an advanced AI that can read and reason like a human.

Weighing Conflicting Information & Advice History
The AI acts as your central analyst. Its greatest strength is its ability to weigh conflicting information between technical indicators and fundamental news.

Traditional computer programs would just see a failing technical indicator and tell you to sell. But our AI reads the context. It synthesizes the data and realizes the stock's technical drop is unwarranted given the global news, formulating a high-conviction recommendation to HOLD.

Furthermore, the system is context-aware. It maintains a rolling, self-cleaning Daily Advice History covering the last 5 business days. When the AI generates a new dossier, it reads its own past advice, ensuring its trading thesis remains consistent and logical throughout the week.
"""

    # ---------------- PAGE 6 ----------------
    page_6 = """
6. The Execution: Seamless Telegram Integration

The final step is delivering this advice to you and executing your trades. We designed this to be as easy as texting a friend, using the secure Telegram messaging app on your phone.

Background Schedulers & End of Day Summaries
The system uses background cron jobs to stay fully engaged. It sends you actionable, intraday trading recommendations every hour. Then, precisely at 4:05 PM ET after the market closes, it shifts gears: it suppresses active trading advice and delivers a comprehensive End-of-Day Summary, reviewing your portfolio's daily performance and outlining expectations for tomorrow.

Conversational Trade Tracking & Confirmations
To record a trade, simply reply to the bot: "I sold 20 shares at $63.40." The AI uses a highly-optimized, Two-Step Verification process to instantly extract the trade intent without burning excess API tokens. 

Before modifying your ledger, the system stages the trade in memory and explicitly asks you for confirmation (YES/NO). Once confirmed, it updates your CSV ledger and recalculates your cost base in real-time, creating a fully automated, risk-free trading desk experience.
"""

    pages = [page_1, page_2, page_3, page_4, page_5, page_6]

    def write_content(content):
        for line in content.split('\n'):
            if line.strip() == '':
                pdf.ln(5)
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or line.startswith('5.') or line.startswith('6.'):
                pdf.set_font("helvetica", 'B', 14)
                pdf.write(8, line.strip() + "\n")
                pdf.set_font("helvetica", size=12)
            elif sum(1 for c in line if c.isupper()) > 2 and len(line) < 40 and not line.endswith('.'):
                pdf.set_font("helvetica", 'B', 12)
                pdf.write(8, line.strip() + "\n")
                pdf.set_font("helvetica", size=12)
            else:
                pdf.write(7, line.strip() + "\n")

    for i, page_content in enumerate(pages):
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        write_content(page_content)

    pdf.output("TSX_Assistant_Guide_Final.pdf")

if __name__ == "__main__":
    create_pdf()
