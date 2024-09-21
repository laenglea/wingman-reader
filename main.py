from typing import Optional
import uvicorn

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Header, Response
from markdownify import markdownify as md
from playwright.async_api import async_playwright, Playwright

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

async def read(url, format="text"):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        try:
            page = await browser.new_page()
            await page.goto(url, wait_until='networkidle')

            match format: 
                case "text" | "markdown":
                    content = await page.content()
                    text = md(content)
                    return Response(content=text, media_type='text/markdown')
                 
                case "html":
                    content = await page.content()
                    return Response(content=content, media_type='text/html')
                 
                case "pdf":
                    content = await page.pdf()
                    return Response(content=content, media_type='application/pdf')
                 
                case _:
                    raise HTTPException(status_code=400, detail="Invalid format")
                 
        except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            

        finally:
            await browser.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)