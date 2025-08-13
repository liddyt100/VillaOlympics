# sanity.py
import pygame, asyncio
pygame.init()
screen = pygame.display.set_mode((800, 450))
clock = pygame.time.Clock()

async def main():
    x = 0
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
        screen.fill((30, 30, 35))
        pygame.draw.circle(screen, (200, 200, 240), (int(x)%800, 225), 30)
        pygame.display.flip()
        clock.tick(60)
        x += 3
        await asyncio.sleep(0)
    pygame.quit()

try:
    import asyncio
    asyncio.run(main())
except RuntimeError:
    pass
