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

Dynamic Ledger Management
Knowing the current price of a stock is only helpful if you know what you originally paid for it. The system maintains a private, automated CSV ledger that records every trade you make. 

Using this ledger, the system constantly calculates your Adjusted Cost Base (ACB). By comparing the live market price to your exact ACB, the system instantly knows if you are sitting on a profit or a loss. It also tracks your exact cash balance, ensuring it never recommends a trade you don't have the funds to execute.
"""

    # ---------------- PAGE 3 ----------------
    page_3 = """
3. The Qualitative Side: Understanding Micro News

While the numbers tell us what a stock is worth right now, the news tells us where the stock might be heading tomorrow. This is called Qualitative Analysis. 

The system doesn't just look at a generic news feed. It specifically targets and pulls the 10 most recent news headlines for each individual asset you own. We call this "Micro News."

Company-Specific Headlines
By pulling news directly related to CNQ.TO or ABX.TO, the system is looking for direct catalysts. These are specific events that directly impact the company's bottom line. 

For example, the system will pick up on headlines about a new earnings report, a change in the company's leadership, an analyst upgrading the stock's rating, or a successful new drilling project. 

These qualitative metrics are crucial. A stock's price might be dropping today, but if the system reads a headline that the company just discovered a massive new gold deposit, it knows that the long-term outlook is actually very positive.
"""

    # ---------------- PAGE 4 ----------------
    page_4 = """
4. The Qualitative Side: Understanding Macro News

Looking only at company-specific news is not enough. Stocks do not exist in a vacuum; they are heavily influenced by the broader global economy. To capture this, the system also pulls headlines for major commodities, specifically WTI Crude Oil and Spot Gold. We call this "Macro News."

Global Events and Sentiment
The system monitors these broader topics to understand global market sentiment. 

For example, geopolitical tensions in the Middle East will often cause Crude Oil prices to spike. When the system reads headlines about these global tensions, it understands the underlying economic metric: global oil supply is threatened, so oil prices are rising.

Because you own Canadian Natural Resources (an oil company), the system connects these dots. It recognizes that even if CNQ hasn't released any company news today, the broader Macro environment for oil is highly bullish. This global qualitative data is often the strongest indicator of how a resource stock will perform in the coming days.
"""

    # ---------------- PAGE 5 ----------------
    page_5 = """
5. The Synthesis: How the AI Makes Decisions

With all the numbers (Quantitative) and the news (Qualitative) gathered, the system must now make a decision. To do this, it packages all this data into a "Dossier" and hands it to a Large Language Model (LLM) - an advanced AI that can read and reason like a human.

Weighing Conflicting Information
The AI acts as your central analyst. Its greatest strength is its ability to weigh conflicting information between technical indicators and fundamental news.

Imagine your Canadian Natural Resources stock has dropped below its 50-day Simple Moving Average, and its RSI indicates it is being heavily sold off (negative Quantitative metrics). However, the AI reads the latest headlines and sees that global oil prices are surging due to an international supply shortage (a positive Qualitative metric). 

Traditional computer programs would just see a failing technical indicator and tell you to sell. But our AI reads the context. It synthesizes the data and realizes the stock's technical drop is unwarranted given the global news. Instead of panicking, it formulates a high-conviction recommendation to HOLD your position, relying entirely on data rather than emotion.
"""

    # ---------------- PAGE 6 ----------------
    page_6 = """
6. The Execution: Seamless Telegram Integration

The final step is delivering this advice to you and executing your trades. We designed this to be as easy as texting a friend, using the secure Telegram messaging app on your phone.

Hourly Push Notifications
Using an automated background scheduler, the system wakes up every hour while the stock market is open. It runs the entire analysis process described above in just a few seconds and sends you a text message with its final recommendation.

Conversational Trade Tracking
If you decide to follow the AI's advice and sell a stock, you don't have to log into a complicated accounting software to record the trade. You simply reply to the Telegram message with a normal sentence, like: "Okay, I sold 20 shares of CNQ at $63.40."

A background program is always listening. The AI reads your casual text message, extracts the exact ticker, price, and quantity, and automatically updates your ledger for you. It recalculates your cash balance and your new Cost Base instantly. This creates a fully automated, closed-loop system where you get all the benefits of an active trading desk with none of the administrative friction.
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
