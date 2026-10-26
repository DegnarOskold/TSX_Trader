import datetime
import fitz  # PyMuPDF
from fpdf import FPDF

class UserGuidePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.set_auto_page_break(auto=False)
        self.set_margins(12, 10, 12)

def generate_guide(output_path="TSX_Trader_Quick_Start_Guide.pdf"):
    pdf = UserGuidePDF()
    pdf.add_page()

    # Dimensions: Letter is 215.9 x 279.4 mm
    page_w = 215.9
    margin = 12.0
    content_w = page_w - (margin * 2)  # 191.9 mm

    # Colors
    c_navy = (16, 24, 40)          # Dark header slate/navy
    c_blue = (37, 99, 235)         # Primary action blue
    c_blue_tint = (239, 246, 255)  # Light blue fill
    c_emerald = (16, 149, 106)     # Green / profit / safety
    c_emerald_tint = (240, 253, 244)
    c_rose = (225, 29, 72)         # Rose / Stop loss
    c_rose_tint = (255, 241, 242)
    c_amber = (217, 119, 6)        # Amber / caution
    c_amber_tint = (254, 243, 199)
    c_card_bg = (248, 250, 252)    # Slate card bg
    c_card_border = (226, 232, 240)
    c_text_dark = (30, 41, 59)
    c_text_muted = (100, 116, 139)

    # -------------------------------------------------------------
    # 1. HEADER BANNER (y: 10 to 34, h=24)
    # -------------------------------------------------------------
    y_start = 10.0
    banner_h = 24.0

    # Header Card Background
    pdf.set_fill_color(*c_navy)
    pdf.rect(margin, y_start, content_w, banner_h, style='F', round_corners=True, corner_radius=3)

    # Accent Stripe on Left
    pdf.set_fill_color(*c_blue)
    pdf.rect(margin + 2.5, y_start + 3.5, 2.5, banner_h - 7.0, style='F', round_corners=True, corner_radius=1)

    # Title & Subtitle
    pdf.set_xy(margin + 8, y_start + 4.0)
    pdf.set_font("helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 6.5, "TSX-TRADER  |  Daily Quick-Start Guide", align="L")

    pdf.set_xy(margin + 8, y_start + 11.8)
    pdf.set_font("helvetica", "", 8.8)
    pdf.set_text_color(195, 208, 226)
    # chr(183) is middle-dot in latin-1
    pdf.cell(115, 5.0, f"Your AI Market Assistant for Wealthsimple  {chr(183)}  What It Does & Your Daily Role", align="L")

    # Badges on the right of header
    badge_w = 32.0
    badge_h = 6.2
    bx = margin + content_w - (badge_w * 2) - 5

    # Badge 1: Co-Pilot Mode
    pdf.set_xy(bx, y_start + 8.8)
    pdf.set_fill_color(30, 41, 65)
    pdf.set_draw_color(59, 130, 246)
    pdf.set_line_width(0.3)
    pdf.rect(bx, y_start + 8.8, badge_w, badge_h, style='FD', round_corners=True, corner_radius=2)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(147, 197, 253)
    pdf.cell(badge_w, badge_h, "CO-PILOT MODE", align="C")

    # Badge 2: Wealthsimple Ready
    bx2 = bx + badge_w + 3.0
    pdf.set_xy(bx2, y_start + 8.8)
    pdf.set_fill_color(20, 83, 45)
    pdf.set_draw_color(34, 197, 94)
    pdf.rect(bx2, y_start + 8.8, badge_w + 1, badge_h, style='FD', round_corners=True, corner_radius=2)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(187, 247, 208)
    pdf.cell(badge_w + 1, badge_h, "WEALTHSIMPLE READY", align="C")

    # -------------------------------------------------------------
    # 2. SECTION: THE CORE IDEA - CO-PILOT, NOT AUTOPILOT (y: 37, h=35)
    # -------------------------------------------------------------
    y_sec1 = 37.0
    sec1_h = 35.0
    card_w = (content_w - 5.0) / 2.0  # 93.45 mm each

    # Card 1: What the Bot Does
    pdf.set_fill_color(*c_card_bg)
    pdf.set_draw_color(*c_card_border)
    pdf.set_line_width(0.3)
    pdf.rect(margin, y_sec1, card_w, sec1_h, style='FD', round_corners=True, corner_radius=3)

    # Card 1 Header Pill
    pdf.set_fill_color(*c_blue_tint)
    pdf.rect(margin + 4, y_sec1 + 3.5, 45, 5.5, style='F', round_corners=True, corner_radius=1.5)
    pdf.set_xy(margin + 4, y_sec1 + 3.5)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*c_blue)
    pdf.cell(45, 5.5, " WHAT THE BOT DOES", align="L")

    # Card 1 Bullets
    pdf.set_text_color(*c_text_dark)
    pdf.set_font("helvetica", "", 7.8)
    bullets_bot = [
        "- Scans TSX momentum, Bank of Canada & Fed news, and commodity trends (crude oil, gold).",
        "- Spots high-probability setups so you never have to sit watching stock charts.",
        "- Sends ready-to-execute trade plans with exact prices directly to your Telegram."
    ]
    by = y_sec1 + 10.2
    for b in bullets_bot:
        pdf.set_xy(margin + 4, by)
        pdf.multi_cell(card_w - 8, 3.7, b)
        by = pdf.get_y() + 1.2

    # Card 2: What You Do
    x_c2 = margin + card_w + 5.0
    pdf.set_fill_color(*c_card_bg)
    pdf.set_draw_color(*c_card_border)
    pdf.rect(x_c2, y_sec1, card_w, sec1_h, style='FD', round_corners=True, corner_radius=3)

    # Card 2 Header Pill
    pdf.set_fill_color(*c_emerald_tint)
    pdf.rect(x_c2 + 4, y_sec1 + 3.5, 50, 5.5, style='F', round_corners=True, corner_radius=1.5)
    pdf.set_xy(x_c2 + 4, y_sec1 + 3.5)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*c_emerald)
    pdf.cell(50, 5.5, " YOUR ROLE (YOU'RE IN CONTROL)", align="L")

    # Card 2 Bullets
    pdf.set_text_color(*c_text_dark)
    pdf.set_font("helvetica", "", 7.8)
    bullets_user = [
        "- You decide whether to take any trade (zero pressure, zero rush to act).",
        "- You place buys & sells inside your Wealthsimple app in 1 to 2 minutes.",
        "- Complete security: the bot has NO access to your money, broker, or accounts."
    ]
    by2 = y_sec1 + 10.2
    for b in bullets_user:
        pdf.set_xy(x_c2 + 4, by2)
        pdf.multi_cell(card_w - 8, 3.7, b)
        by2 = pdf.get_y() + 1.2

    # -------------------------------------------------------------
    # 3. SECTION: ANATOMY OF A TRADE ALERT (y: 75, h=42)
    # -------------------------------------------------------------
    y_sec2 = 75.0
    sec2_h = 42.0

    pdf.set_fill_color(*c_card_bg)
    pdf.set_draw_color(*c_card_border)
    pdf.rect(margin, y_sec2, content_w, sec2_h, style='FD', round_corners=True, corner_radius=3)

    # Title
    pdf.set_xy(margin + 4, y_sec2 + 3.2)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*c_navy)
    pdf.cell(90, 5, "ANATOMY OF A TRADE ALERT (ZERO GUESSWORK)", align="L")

    pdf.set_xy(margin + 98, y_sec2 + 3.2)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(*c_text_muted)
    pdf.cell(content_w - 102, 5, "Every signal includes clear math so you never have to guess.", align="R")

    # 3 Visual Price Boxes Side-by-Side
    box_w = (content_w - 16.0) / 3.0  # ~58.6 mm each
    box_h = 20.0
    box_y = y_sec2 + 9.5

    # Box 1: Entry Price
    bx1 = margin + 4
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(190, 205, 230)
    pdf.rect(bx1, box_y, box_w, box_h, style='FD', round_corners=True, corner_radius=2)
    pdf.set_xy(bx1, box_y + 1.8)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_blue)
    pdf.cell(box_w, 4, "1. ENTRY PRICE", align="C")
    pdf.set_xy(bx1, box_y + 5.5)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*c_text_dark)
    pdf.cell(box_w, 5.5, "$52.40", align="C")
    pdf.set_xy(bx1 + 2, box_y + 11.2)
    pdf.set_font("helvetica", "", 7)
    pdf.set_text_color(*c_text_muted)
    pdf.multi_cell(box_w - 4, 3.2, "Suggested buy level based on momentum & volume.", align="C")

    # Box 2: Target Sell Price
    bx2 = bx1 + box_w + 4.0
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(167, 243, 208)
    pdf.rect(bx2, box_y, box_w, box_h, style='FD', round_corners=True, corner_radius=2)
    pdf.set_xy(bx2, box_y + 1.8)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_emerald)
    pdf.cell(box_w, 4, "2. TARGET PROFIT", align="C")
    pdf.set_xy(bx2, box_y + 5.5)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*c_emerald)
    pdf.cell(box_w, 5.5, "$54.80  (+4.6%)", align="C")
    pdf.set_xy(bx2 + 2, box_y + 11.2)
    pdf.set_font("helvetica", "", 7)
    pdf.set_text_color(*c_text_muted)
    pdf.multi_cell(box_w - 4, 3.2, "Pre-calculated profit level to lock in short-term gains.", align="C")

    # Box 3: Stop-Loss Price
    bx3 = bx2 + box_w + 4.0
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(254, 205, 211)
    pdf.rect(bx3, box_y, box_w, box_h, style='FD', round_corners=True, corner_radius=2)
    pdf.set_xy(bx3, box_y + 1.8)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_rose)
    pdf.cell(box_w, 4, "3. STOP-LOSS EXIT", align="C")
    pdf.set_xy(bx3, box_y + 5.5)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*c_rose)
    pdf.cell(box_w, 5.5, "$50.90  (-2.9%)", align="C")
    pdf.set_xy(bx3 + 2, box_y + 11.2)
    pdf.set_font("helvetica", "", 7)
    pdf.set_text_color(*c_text_muted)
    pdf.multi_cell(box_w - 4, 3.2, "Pre-set safety exit. Caps your maximum loss on entry.", align="C")

    # Bottom Callout inside Section 2
    pdf.set_xy(margin + 4, box_y + box_h + 2.5)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_navy)
    pdf.cell(30, 4, "Commodity Shield:", align="L")
    pdf.set_xy(margin + 33, box_y + box_h + 2.5)
    pdf.set_font("helvetica", "", 7.5)
    pdf.set_text_color(*c_text_muted)
    pdf.cell(content_w - 38, 4, "For Oil & Energy stocks, the bot verifies crude oil prices are positive before recommending.", align="L")

    # -------------------------------------------------------------
    # 4. SECTION: YOUR 3-STEP DAILY WORKFLOW (y: 120, h=78)
    # -------------------------------------------------------------
    y_sec3 = 120.0
    sec3_h = 78.0

    pdf.set_fill_color(*c_card_bg)
    pdf.set_draw_color(*c_card_border)
    pdf.rect(margin, y_sec3, content_w, sec3_h, style='FD', round_corners=True, corner_radius=3)

    # Title
    pdf.set_xy(margin + 4, y_sec3 + 3.0)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*c_navy)
    pdf.cell(100, 5, "YOUR DAILY ROUTINE  |  FROM ALERT TO PROFIT IN 3 STEPS", align="L")

    # Step Card 1: Alert Received (y: 128.5, h=20.5)
    s1_y = y_sec3 + 8.5
    s1_h = 20.5
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*c_card_border)
    pdf.rect(margin + 3, s1_y, content_w - 6, s1_h, style='FD', round_corners=True, corner_radius=2)

    # Step 1 Pill
    pdf.set_fill_color(*c_blue)
    pdf.rect(margin + 5, s1_y + 3, 14, 5, style='F', round_corners=True, corner_radius=1)
    pdf.set_xy(margin + 5, s1_y + 3)
    pdf.set_font("helvetica", "B", 7)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(14, 5, "STEP 1", align="C")

    pdf.set_xy(margin + 22, s1_y + 3)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(*c_text_dark)
    pdf.cell(85, 5, "Check Telegram Notification (Market Hours: 9:30 AM - 4:00 PM ET)")
    pdf.set_xy(margin + 120, s1_y + 3)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(*c_text_muted)
    pdf.cell(content_w - 128, 5, "Time needed: ~30 seconds", align="R")

    pdf.set_xy(margin + 22, s1_y + 8.2)
    pdf.set_font("helvetica", "", 7.8)
    pdf.set_text_color(*c_text_dark)
    pdf.multi_cell(content_w - 28, 3.8,
        "When a BUY alert pings your Telegram, quickly glance at the company and price targets. "
        "If you like the idea, move to Step 2. If you are busy or not interested, simply skip it! You are never obligated to trade.")

    # Step Card 2: Place & Text Bot (y: 151.5, h=22.0)
    s2_y = s1_y + s1_h + 2.5
    s2_h = 22.0
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*c_card_border)
    pdf.rect(margin + 3, s2_y, content_w - 6, s2_h, style='FD', round_corners=True, corner_radius=2)

    # Step 2 Pill
    pdf.set_fill_color(*c_emerald)
    pdf.rect(margin + 5, s2_y + 3, 14, 5, style='F', round_corners=True, corner_radius=1)
    pdf.set_xy(margin + 5, s2_y + 3)
    pdf.set_font("helvetica", "B", 7)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(14, 5, "STEP 2", align="C")

    pdf.set_xy(margin + 22, s2_y + 3)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(*c_text_dark)
    pdf.cell(85, 5, "Execute in Wealthsimple & Text the Bot Naturally")
    pdf.set_xy(margin + 120, s2_y + 3)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(*c_text_muted)
    pdf.cell(content_w - 128, 5, "Time needed: ~2 minutes", align="R")

    pdf.set_xy(margin + 22, s2_y + 8.2)
    pdf.set_font("helvetica", "", 7.8)
    pdf.set_text_color(*c_text_dark)
    pdf.multi_cell(content_w - 28, 3.8,
        "1. Open Wealthsimple, buy your desired shares, and enter a stop-loss using the alert's safety price.\n"
        "2. Then just text the bot naturally on Telegram (e.g. \"Bought 20 shares of SU at 52.40\"). "
        "No complex syntax or commands needed -- the AI understands plain conversation and logs it for you!")

    # Step Card 3: The +2% Breakeven Rule (y: 176.0, h=21.0)
    s3_y = s2_y + s2_h + 2.5
    s3_h = 21.0
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(167, 243, 208)
    pdf.rect(margin + 3, s3_y, content_w - 6, s3_h, style='FD', round_corners=True, corner_radius=2)

    # Step 3 Pill
    pdf.set_fill_color(13, 148, 136)
    pdf.rect(margin + 5, s3_y + 3, 14, 5, style='F', round_corners=True, corner_radius=1)
    pdf.set_xy(margin + 5, s3_y + 3)
    pdf.set_font("helvetica", "B", 7)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(14, 5, "STEP 3", align="C")

    pdf.set_xy(margin + 22, s3_y + 3)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(*c_text_dark)
    pdf.cell(90, 5, "The +2% Breakeven Rule (Protecting Your Principal)")
    pdf.set_xy(margin + 120, s3_y + 3)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_emerald)
    pdf.cell(content_w - 128, 5, "* CAPITAL DEFENSE *", align="R")

    pdf.set_xy(margin + 22, s3_y + 8.2)
    pdf.set_font("helvetica", "", 7.8)
    pdf.set_text_color(*c_text_dark)
    pdf.multi_cell(content_w - 28, 3.8,
        "When your stock gains +2% above your cost basis, the bot alerts you: \"Move Stop-Loss to Breakeven\". "
        "Update your stop in Wealthsimple to your purchase price. This protects your downside on the trade so you can let winning momentum run without risking a loss on the position.")

    # -------------------------------------------------------------
    # 5. SECTION: THREE GOLDEN RULES (y: 201, h=56)
    # -------------------------------------------------------------
    y_sec4 = 201.0
    sec4_h = 56.0

    pdf.set_fill_color(*c_card_bg)
    pdf.set_draw_color(*c_card_border)
    pdf.rect(margin, y_sec4, content_w, sec4_h, style='FD', round_corners=True, corner_radius=3)

    # Title
    pdf.set_xy(margin + 4, y_sec4 + 3.0)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*c_navy)
    pdf.cell(100, 5, "THREE GOLDEN RULES FOR TOTAL PEACE OF MIND", align="L")

    # 3 Mini Cards Side-by-Side
    mini_w = (content_w - 14.0) / 3.0  # ~59.3 mm each
    mini_h = 44.0
    mini_y = y_sec4 + 8.5

    # Rule 1: Respect the Stop-Loss
    mx1 = margin + 4
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(254, 205, 211)
    pdf.rect(mx1, mini_y, mini_w, mini_h, style='FD', round_corners=True, corner_radius=2)

    # Rule 1 Badge
    pdf.set_fill_color(*c_rose_tint)
    pdf.rect(mx1 + 3, mini_y + 2.5, mini_w - 6, 5, style='F', round_corners=True, corner_radius=1)
    pdf.set_xy(mx1 + 3, mini_y + 2.5)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_rose)
    pdf.cell(mini_w - 6, 5, "1. RESPECT THE STOP-LOSS", align="C")

    pdf.set_xy(mx1 + 3, mini_y + 9.5)
    pdf.set_font("helvetica", "", 7.5)
    pdf.set_text_color(*c_text_dark)
    pdf.multi_cell(mini_w - 6, 3.6,
        "Every trade has risk -- the initial risk is losing down to the stop-loss level.\n\n"
        "Never cancel or lower your stop hoping a falling stock bounces back. Cutting losses early is what preserves your trading capital.")

    # Rule 2: Midday Break
    mx2 = mx1 + mini_w + 3.0
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(253, 230, 138)
    pdf.rect(mx2, mini_y, mini_w, mini_h, style='FD', round_corners=True, corner_radius=2)

    # Rule 2 Badge
    pdf.set_fill_color(*c_amber_tint)
    pdf.rect(mx2 + 3, mini_y + 2.5, mini_w - 6, 5, style='F', round_corners=True, corner_radius=1)
    pdf.set_xy(mx2 + 3, mini_y + 2.5)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_amber)
    pdf.cell(mini_w - 6, 5, "2. THE LUNCHTIME BREAK", align="C")

    pdf.set_xy(mx2 + 3, mini_y + 9.5)
    pdf.set_font("helvetica", "", 7.5)
    pdf.set_text_color(*c_text_dark)
    pdf.multi_cell(mini_w - 6, 3.6,
        "The bot deliberately avoids initiating buys between 11:30 AM and 2:00 PM ET.\n\n"
        "Lunch hours suffer from low volume and deceptive fake-outs. Step away, enjoy your day, and let the system wait for clean setups.")

    # Rule 3: End of Day Summary
    mx3 = mx2 + mini_w + 3.0
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(190, 205, 230)
    pdf.rect(mx3, mini_y, mini_w, mini_h, style='FD', round_corners=True, corner_radius=2)

    # Rule 3 Badge
    pdf.set_fill_color(*c_blue_tint)
    pdf.rect(mx3 + 3, mini_y + 2.5, mini_w - 6, 5, style='F', round_corners=True, corner_radius=1)
    pdf.set_xy(mx3 + 3, mini_y + 2.5)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_blue)
    pdf.cell(mini_w - 6, 5, "3. DAILY 4:05 PM SUMMARY", align="C")

    pdf.set_xy(mx3 + 3, mini_y + 9.5)
    pdf.set_font("helvetica", "", 7.5)
    pdf.set_text_color(*c_text_dark)
    pdf.multi_cell(mini_w - 6, 3.6,
        "Every market close at 4:05 PM ET, the bot sends a concise recap to Telegram.\n\n"
        "Spend 1 minute reviewing your open positions, unrealized profits, and market trends. You never have to do math or track spreadsheets!")

    # -------------------------------------------------------------
    # 6. FOOTER (y: 260, h=10)
    # -------------------------------------------------------------
    y_footer = 260.0
    pdf.set_draw_color(*c_card_border)
    pdf.line(margin, y_footer, margin + content_w, y_footer)

    pdf.set_xy(margin, y_footer + 2.0)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*c_navy)
    pdf.cell(58, 4, "TSX-TRADER PERSONAL EDITION", align="L")

    pdf.set_xy(margin + 58, y_footer + 2.0)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(*c_emerald)
    pdf.cell(content_w - 108, 4, "\"Plan the trade, protect your capital, and let the math do the work.\"", align="C")

    pdf.set_xy(margin + content_w - 50, y_footer + 2.0)
    pdf.set_font("helvetica", "", 7.5)
    pdf.set_text_color(*c_text_muted)
    date_str = datetime.date.today().strftime("%B %Y")
    pdf.cell(50, 4, f"Updated: {date_str} | Page 1 of 1", align="R")

    # Output file
    pdf.output(output_path)
    print(f"Generated PDF saved to {output_path}")

    # Verify page count
    doc = fitz.open(output_path)
    print(f"Verified Page Count: {len(doc)}")
    assert len(doc) == 1, f"Error: PDF has {len(doc)} pages, expected 1!"

if __name__ == "__main__":
    generate_guide()
