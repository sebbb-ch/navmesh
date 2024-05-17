import pygame 
clock = pygame.time.Clock()
from pygame.locals import *
from utils import *

frame_start = 0
frame_end = pygame.time.get_ticks()
dt = frame_end - frame_start

# shape : list = createPolygon((100, 100), 4, 30)
obstacles = populateEnvironment()
# shape = createPolygon((100,100), 3, 30)

original_edges = []
all_vertices = [(0,0), (WIN_WIDTH, 0), (0, WIN_HEIGHT), (WIN_WIDTH, WIN_HEIGHT)]
for poly in obstacles :
    # a surprise tool that will help us later
    # save a list of the edges that make up the world right now, before any triangulation
    # to help distinguish between what to merge and what not to merge later
    for i in range(len(poly)):
        original_edges.append((poly[i], poly[(i + 1) % len(poly)]))

    # create naive list of vertices
    for vertex in poly :
        all_vertices.append(vertex)

triangles = delaunay(all_vertices)
merged = mergeTriangles(triangles, original_edges)
centroids = [findCentroid(tri) for tri in merged] 
midpoints = []
for poly in merged :
    # find midpoints
    n = len(poly)
    for i in range(n) :
        edge = (poly[i], poly[(i + 1) % n])
        mid = findMidpoint(edge[0], edge[1])
        if mid not in midpoints :
            midpoints.append(mid)
network = []

while playing:
    raw_window.fill((0,0,0))

    for event in pygame.event.get() :
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN : 
            if event.key == K_ESCAPE:
               playing = False
    
    # for index, point in enumerate(shape):
    #     pygame.draw.line(raw_window, (240, 240, 240), point, shape[index - 1], 2)

    # for obj in obstacles :
    #     # NOTE : this is cheating a little bit, the collidepoint part in particular
    #     # https://gamedev.stackexchange.com/questions/181692/pygame-polygon-click-detection
    #     pygame.draw.polygon(raw_window, (255,255,255), obj)
    #     # for index, point in enumerate(obj):
    #     #     pygame.draw.line(raw_window, (240, 240, 240), point, obj[index - 1], 2)

    for tri in merged :
        pygame.draw.polygon(raw_window, (255,0,0), tri, 1)
        # center = findCentroid(tri)s
        # pygame.draw.circle(raw_window, (0,255,0), center, 3)

    valid_centroids = []
    for pt in centroids :
        valid = True
        for obj in obstacles :
            # this is where the cheating happens because we're actually drawing the polygons way too many times
            if pygame.draw.polygon(raw_window, (255,255,255), obj).collidepoint(pt):
                valid = False

        if valid :
            valid_centroids.append(pt)

    for pt in valid_centroids : 
        pygame.draw.circle(raw_window, (0,255,0), pt, 3)
    #  ========

    valid_midpoints = []
    for pt in midpoints :
        valid = True 
        # if on outer edge :
        if pt[0] == 0 or pt[0] == WIN_WIDTH :
            valid = False
        if pt[1] == 0 or pt[1] == WIN_HEIGHT :
            valid = False

        for obj in obstacles :
            if pygame.draw.polygon(raw_window, (255,255,255), obj).collidepoint(pt):
                valid = False
        if valid :
            valid_midpoints.append(pt)

    for pt in valid_midpoints : 
        pygame.draw.circle(raw_window, (0,0,255), pt, 3)


    # ==============================
    scaled_window = pygame.transform.scale(raw_window, display_window.get_size())
    display_window.blit(scaled_window, (0,0))
    pygame.display.update()
    # ==============================
    frame_end = pygame.time.get_ticks()
    dt = frame_end - frame_start
    clock.tick(60)

pygame.quit()
sys.exit()