import os
import re
import uvicorn
import html2text

from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Header, Response
from urllib.parse import urlparse
from markdownify import markdownify as md
from playwright.async_api import async_playwright

app = FastAPI(
    title="LLM Platform Reader"
)

class ReadRequest(BaseModel):
    url: str
    format: str = "text"

@app.get("/{url:path}")
async def read_get(url: str, x_return_format: Optional[str] = Header('text')):
    url = url.lstrip('/')
    format = x_return_format
    
    return await read(url, format)

@app.post("/")
async def read(request: ReadRequest, x_return_format: Optional[str] = Header(None)):
    url = request.url
    format = request.format
    
    if x_return_format:
        format = x_return_format
        
    return await read(url, format)

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

async def read(url, format="text"):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    async with async_playwright() as p:
        launch_args = {}

        if settings := get_proxy_settings():
            launch_args["proxy"] = settings

        browser = await p.chromium.launch(**launch_args)

        try:
            context = await browser.new_context(
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
            )
            
            page = await context.new_page()

            await page.goto(url, wait_until='networkidle')

            match format:
                case "text":
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    
                    content = await page.content()
                    content = h.handle(content)
                    
                    content = re.sub(r'^\s*\d+\s*$', '', content, flags=re.MULTILINE)
                    content = re.sub(r'^\s*$', '', content, flags=re.MULTILINE)
                    
                    return Response(content=content, media_type='text/plain')
                
                case "markdown":
                    content = md(await page.content(), heading_style='ATX')
                    return Response(content=content, media_type='text/markdown')
                 
                case "html":
                    content = await page.content()
                    return Response(content=content, media_type='text/html')
                 
                case "pdf":
                    content = await page.pdf()
                    return Response(content=content, media_type='application/pdf')
                
                case "screenshot":
                    data = await page.screenshot()
                    return Response(content=data, media_type='image/png')
                
                case "pageshot":
                    data = await page.screenshot(full_page=True)
                    return Response(content=data, media_type='image/png')
                 
                case _:
                    raise HTTPException(status_code=400, detail="Invalid format")
                 
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            

        finally:
            await browser.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)