"""Email renderer for generating HTML reports using Jinja2 templates."""

from datetime import datetime
from typing import List

from jinja2 import Environment, PackageLoader, select_autoescape

from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class EmailRenderer:
    """Renders HTML email templates using Jinja2."""

    def __init__(self) -> None:
        """
        Initialize the email renderer with Jinja2 environment.

        Sets up template loading from the smart_money_tracker/email/templates
        directory with autoescape enabled for security (XSS prevention).
        """
        self.env = Environment(
            loader=PackageLoader("smart_money_tracker", "email/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        logger.info("EmailRenderer initialized with Jinja2 environment")

    def render(
        self,
        stocks: List[dict],
        generated_at: datetime,
        tips_india: List[dict] | None = None,
        tips_us: List[dict] | None = None,
    ) -> str:
        """
        Render the daily report HTML template.

        Args:
            stocks: List of stock dictionaries with structure:
                {
                    "ticker": str,
                    "score": int,
                    "reasons": List[str],
                    "analysis": {
                        "bullish_thesis": str,
                        "bearish_thesis": str,
                        "key_risks": str
                    },
                    "notable_activity": str (optional)
                }
            generated_at: Datetime when the report was generated

        Returns:
            HTML string with rendered template

        Raises:
            Exception: If template loading or rendering fails
        """
        try:
            template = self.env.get_template("daily_report.html")

            # Format datetime as ISO string for readability
            timestamp_str = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

            # Render template with context
            html_output = template.render(
                stocks=stocks,
                generated_at=timestamp_str,
                tips_india=tips_india or [],
                tips_us=tips_us or [],
            )

            logger.info(
                f"Successfully rendered email template for {len(stocks)} stock(s), "
                f"{len(tips_india or [])} India tips, {len(tips_us or [])} US tips"
            )
            return html_output

        except Exception as e:
            logger.error(f"Error rendering email template: {type(e).__name__}: {str(e)}")
            raise
