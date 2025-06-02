import os
import grpc
import asyncio

from concurrent import futures
from grpc_reflection.v1alpha import reflection

from urllib.parse import urlparse
from fake_useragent import UserAgent

from markdownify import markdownify as md
from patchright.async_api import async_playwright

import extractor_pb2
import extractor_pb2_grpc

ua = UserAgent(browsers=['Edge', 'Chrome'], platforms=['Windows'])

def get_proxy_settings() -> dict:
    settings: dict = {}

    proxy_url = (
        os.getenv("https_proxy") or
        os.getenv("HTTPS_PROXY") or
        os.getenv("http_proxy") or
        os.getenv("HTTP_PROXY")
    )

    if proxy_url:
        p = urlparse(proxy_url)

        settings["server"] = f"{p.scheme}://{p.hostname}:{p.port}"
    
        if p.username:
            settings["username"] = p.username
    
        if p.password:
            settings["password"] = p.password
    
    return settings

class ExtractorServicer(extractor_pb2_grpc.ExtractorServicer):
    async def Extract(self, request: extractor_pb2.ExtractRequest, context: grpc.aio.ServicerContext):
        url = request.url
        format = request.format or extractor_pb2.FORMAT_TEXT

        handle_banners = format in (extractor_pb2.FORMAT_IMAGE, extractor_pb2.FORMAT_PDF)

        if not url:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('URL is required but not provided')
            return extractor_pb2.File()

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        async with async_playwright() as p:
            launch_args = {}

            if settings := get_proxy_settings():
                launch_args["proxy"] = settings
            
            browser = await p.chromium.launch(**launch_args)
            
            browser_context = await browser.new_context(
                ignore_https_errors=True,
                user_agent=ua.random,
                viewport={'width': 1280, 'height': 720},
                reduced_motion='reduce',
            )

            page = await browser_context.new_page()

            if handle_banners:
                await page.route("**/*", lambda route: (
                    route.abort() if route.request.resource_type in ["font", "media", "websocket", "manifest"] 
                    or any(ext in route.request.url for ext in ['.woff', '.woff2', '.ttf', '.otf', '.mp4', '.mp3', '.avi', '.mov'])
                    else route.continue_()
                ))
                
                await page.add_style_tag(content="""
                    *, *::before, *::after {
                        animation-duration: 0s !important;
                        animation-delay: 0s !important;
                        transition-duration: 0s !important;
                        transition-delay: 0s !important;
                        scroll-behavior: auto !important;
                    }
                    video, iframe, embed, object {
                        display: none !important;
                    }
                """)

                await page.add_style_tag(content="""
                    [id*="cookie" i]:not([id*="cookieless" i]),
                    [class*="cookie" i]:not([class*="cookieless" i]),
                    [id*="consent" i],
                    [class*="consent" i],
                    [id*="gdpr" i],
                    [class*="gdpr" i],
                    [aria-modal="true"],
                    .modal-backdrop,
                    .cookie-banner,
                    .consent-banner {
                        display: none !important;
                    }
                """)

            await page.goto(url, wait_until='load')

            if handle_banners:
                accept_selectors = [
                    "button:text-matches('Accept', 'i')",
                    "button:text-matches('Accept all', 'i')",
                    "button:text-matches('Allow all', 'i')",
                    "[id*='accept' i]",
                    "[class*='accept' i]"
                ]
                
                for selector in accept_selectors:
                    try:
                        await page.click(selector, timeout=500)
                        break
                    except:
                        continue
                    
                await page.evaluate("""
                    const bannersToRemove = document.querySelectorAll(`
                        [id*="cookie" i]:not([id*="cookieless" i]),
                        [class*="cookie" i]:not([class*="cookieless" i]),
                        [id*="consent" i],
                        [class*="consent" i],
                        [aria-modal="true"]
                    `);
                    bannersToRemove.forEach(el => el.remove());
                """)

                await page.evaluate("""
                    // Remove any remaining animations or videos
                    document.querySelectorAll('video, iframe, embed, object').forEach(el => el.remove());
                    // Set all images to load immediately
                    document.querySelectorAll('img').forEach(img => {
                        img.loading = 'eager';
                        if (img.src && img.src.startsWith('data:')) return;
                        if (!img.complete) img.src = img.src;
                    });
                """)

            await page.wait_for_load_state('networkidle', timeout=10000)

            match format:
                case extractor_pb2.FORMAT_TEXT:
                    content = await page.content()

                    markdown = md(
                        content,
                        heading_style='ATX',
                        bullets='-',
                        escape_asterisks=False,
                        escape_underscores=False,
                        code_language=True,
                        auto_links=True,
                    )

                    markdown = markdown.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
                    markdown = markdown.replace('\\*', '*')         # Fix over-escaped asterisks
                    markdown = markdown.replace('\\_', '_')         # Fix over-escaped underscores

                    data = bytes(markdown, 'utf-8')

                    with open('page.md', 'wb') as f:
                        f.write(data)

                    return extractor_pb2.File(content=data, content_type='text/markdown')
                 
                case extractor_pb2.FORMAT_IMAGE:
                    data = await page.screenshot(
                        full_page=True,
                        type='png',
                        omit_background=False,
                        animations='disabled'
                    )
                    
                    with open('page.png', 'wb') as f:
                        f.write(data)

                    return extractor_pb2.File(content=data, content_type='image/png')
                
                case extractor_pb2.FORMAT_PDF:
                    data = await page.pdf()
                    return extractor_pb2.File(content=data, content_type='application/pdf')

async def serve():
    max_message_size = 100 * 1024 * 1024

    options = [
        ('grpc.max_receive_message_length', max_message_size),
        ('grpc.max_send_message_length', max_message_size),
    ]

    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=options
    )

    extractor = ExtractorServicer()
    extractor_pb2_grpc.add_ExtractorServicer_to_server(extractor, server)

    SERVICE_NAMES = (
        extractor_pb2.DESCRIPTOR.services_by_name['Extractor'].full_name,
        reflection.SERVICE_NAME,
    )

    reflection.enable_server_reflection(SERVICE_NAMES, server)

    server.add_insecure_port('[::]:50051')
    await server.start()

    print("Wingman Reader started. Listening on port 50051.")
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())