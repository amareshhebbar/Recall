import random
import asyncio

async def human_click(page, selector_or_locator):
    try:
        if isinstance(selector_or_locator, str):
            element = await page.wait_for_selector(selector_or_locator, state="visible", timeout=10000)
        else:
            element = selector_or_locator
            
        if not element:
            return False

        box = await element.bounding_box()
        if not box:
            return False

        x = box["x"] + (box["width"] / 2) + random.uniform(-10, 10)
        y = box["y"] + (box["height"] / 2) + random.uniform(-10, 10)

        await page.mouse.move(x, y, steps=random.randint(15, 25))
        
        await asyncio.sleep(random.uniform(0.2, 0.5))

        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.2)) 
        await page.mouse.up()
        
        return True
    except Exception as e:
        logging.warning(f"Human click failed: {e}")
        return False