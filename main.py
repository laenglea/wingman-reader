import re
import grpc
import asyncio
import html2text

from concurrent import futures
from grpc_reflection.v1alpha import reflection

from markdownify import markdownify as md
from playwright.async_api import async_playwright

import extractor_pb2
import extractor_pb2_grpc

class ExtractorServicer(extractor_pb2_grpc.ExtractorServicer):
    async def Extract(self, request: extractor_pb2.ExtractRequest, context: grpc.aio.ServicerContext):
        url = request.url
        format = request.format or extractor_pb2.FORMAT_TEXT

        if not url:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('URL is required but not provided')
            return extractor_pb2.File()

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        async with async_playwright() as p:
            launch_args = {}
            
            browser = await p.chromium.launch(**launch_args)
            
            browser_context = await browser.new_context(
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
            )

            page = await browser_context.new_page()
            await page.goto(url, wait_until='networkidle', timeout=30000)

            match format:
                case extractor_pb2.FORMAT_TEXT:
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    
                    content = await page.content()
                    content = h.handle(content)
                    
                    content = re.sub(r'^\s*\d+\s*$', '', content, flags=re.MULTILINE)
                    content = re.sub(r'^\s*$', '', content, flags=re.MULTILINE)

                    # content = md(await page.content(), heading_style='ATX')
                    # text/markdown
                    
                    data = bytes(content, 'utf-8')
                    return extractor_pb2.File(content=data, content_type='text/plain')
                 
                case extractor_pb2.FORMAT_IMAGE:
                    data = await page.screenshot(full_page=True)
                    
                    with open('pageshot.png', 'wb') as f:
                        f.write(data)

                    return extractor_pb2.File(content=data, content_type='image/png')
                
                case extractor_pb2.FORMAT_PDF:
                    data = await page.pdf()
                    return extractor_pb2.File(content=data, content_type='application/pdf')

async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

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