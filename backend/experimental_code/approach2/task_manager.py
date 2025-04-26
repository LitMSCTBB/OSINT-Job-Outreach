import asyncio
from typing import Dict

from backend.experimental_code.approach2.company_processor import CompanyProcessor, ProcessingStage
from playwright.async_api import BrowserContext, Page, Browser as PlaywrightBrowser
from browser_use import Browser

class TaskManager:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.playwright_browser: PlaywrightBrowser = None
        self.context: BrowserContext = None
        self.processors: Dict[str, CompanyProcessor] = {}
        # Queue of domains that are ready to process
        self.ready_queue: asyncio.Queue = asyncio.Queue()
        # Set of domains that are waiting for user input
        self.waiting_companies: set = set()

    async def __aenter__(self):
        self.playwright_browser = await self.browser.get_playwright_browser()
        self.context = self.playwright_browser.contexts[0]
        return self

    async def __aexit__(self):
        print("Exiting TaskManager")
        if self.context:
            await self.context.close()

    async def add_company(self, company_url: str, domain: str, rerun_config: Dict[str, bool] = None):
        """Add a new company to process."""
        if domain not in self.processors:
            processor = CompanyProcessor(self.browser, self.context, company_url, domain, rerun_config)
            self.processors[domain] = processor
            # Add to ready queue immediately
            await self.ready_queue.put(domain)
            print(f"Added {domain} to processing queue")

    async def process_companies(self):
        """Process companies from the queue."""
        while True:
            # Check if we're done
            if self.ready_queue.empty() and not self.waiting_companies:
                if all(
                    p.stage == ProcessingStage.COMPLETED
                    for p in self.processors.values()
                ):
                    print("All companies completed processing")
                    break

            try:
                # Get next company from queue with timeout
                domain = await asyncio.wait_for(self.ready_queue.get(), timeout=1.0)
                processor = self.processors[domain]

                # Try to process next step
                try:
                    work_done = await processor.process_next_available_step()

                    if work_done:
                        # If work was done and not completed, queue it again
                        if processor.stage != ProcessingStage.COMPLETED:
                            await self.ready_queue.put(domain)
                    else:
                        # If no work was done, company is waiting for input
                        print(
                            f"{domain} waiting for user input at stage {processor.stage}"
                        )
                        self.waiting_companies.add(domain)

                except Exception as e:
                    print(f"Error processing {domain}: {e}")
                    processor.stage = ProcessingStage.ERROR
                    processor.error = str(e)

            except asyncio.TimeoutError:
                # No companies in queue, just continue loop
                continue

    def notify_user_input(self, domain: str):
        """Notify that user input is available for a company."""
        if domain in self.waiting_companies:
            self.waiting_companies.remove(domain)
            # Put back in ready queue
            asyncio.create_task(self.ready_queue.put(domain))
            print(f"Company {domain} ready to continue processing")

    async def cleanup(self):
        """Clean up all resources."""
        for processor in self.processors.values():
            await processor.cleanup()
