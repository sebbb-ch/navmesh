import pygame, json, random, glob, ast, sys, os, math

# https://stackoverflow.com/questions/13356752/pygame-has-huge-delay-with-playing-sounds
pygame.mixer.pre_init(44100, -16, 2, 256)
pygame.mixer.init()
pygame.init()

WIN_WIDTH = 160 * 2
WIN_HEIGHT = 144 * 2
WIN_SCALE = 3

display_window = pygame.display.set_mode((WIN_WIDTH * WIN_SCALE, WIN_HEIGHT * WIN_SCALE), 0, 32)
raw_window = pygame.Surface((WIN_WIDTH,WIN_HEIGHT))

playing = True

BASE_PATH = './'
def load_image(path):
    img = pygame.image.load(BASE_PATH + path).convert()
    img.set_colorkey((0, 0, 0))
    return img


# generate and place polygons to create the world
# center - tuple coordinates of the center point
# sides - desired number of sides for the polygon
# distance - distance from the center to each vertex of the polygon
# rotation - optional clockwise rotation in degrees to every point on the originally generated polygon
def createPolygon(center : tuple, num_sides: int, radius : int, rot_angle : int = 0):
    vertices = []
    angle_between_vertices = 2 * math.pi / num_sides
    for i in range(num_sides):
        angle   = i * angle_between_vertices + math.radians(rot_angle)
        x       = center[0] + radius * math.cos(angle)
        y       = center[1] + radius * math.sin(angle)
        vertices.append((math.floor(x), math.floor(y)))
    return vertices

def populateEnvironment() :
    polys : list = []
    for y in range(2) :
        center_y = (WIN_HEIGHT * (y+1)) / 2 - (WIN_HEIGHT / 4)
        noise_y = random.randint(-15,15)
        for x in range(3) :
            center_x        = (WIN_WIDTH * (x+1)) / 3 - (WIN_HEIGHT / 6)
            noise_x         = random.randint(-15,15)
            rand_num_sides  = random.randint(3, 7)
            rand_dist       = random.randint(22, 42)
            rand_rot        = random.randint(0, 90)
            polys.append(createPolygon((center_x + noise_x, center_y + noise_y), rand_num_sides, rand_dist, rand_rot))
    return polys

# KEY CONCEPTS:
# Delaunay Triangulation
    # https://en.wikipedia.org/wiki/Delaunay_triangulation
    # https://ianthehenry.com/posts/delaunay/
# Boyer-Watson Algorithm
# Guibas and Stolfi

# https://mathworld.wolfram.com/Circumcircle.html
# https://paulbourke.net/geometry/circlesphere/
# equations are largely copied from wolfram and SO, the math isn't really the point here
# triangle = [(ax, ay), (bx, by), (cx, cy)]
def generateCircumcircle(triangle : list) -> tuple:
    ax, ay = triangle[0]
    bx, by = triangle[1]
    cx, cy = triangle[2]

    # calculate center of the circle determined by the three points of the triangle
    # 1) center must be equidistant to each vertex
    # 2) intersection of perpendicular bisectors
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    center_x = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    center_y = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d

    center = (center_x, center_y)
    radius = math.sqrt((ax - center_x)**2 + (ay - center_y)**2)
    
    return center, radius

def inCircle(point : tuple, circle : tuple):
    center, radius = circle
    px, py = point
    cx, cy = center
    # check distance from center of circle to point
    return math.sqrt((px - cx)**2 + (py - cy)**2) < radius

# NOTE: ALTERNATIVELY the determinant of this matrix (or rather its sign) could tell us if p is contained 
# in the circle defined by a,b,c - this is its own rabbithole, see the ian henry blogpost for more
# [ax , ay, ax^2 + ay^2, 1]
# [bx , by, ax^2 + ay^2, 1]
# [cx , cy, ax^2 + ay^2, 1]
# [px , py, ax^2 + ay^2, 1]

def findMidpoint(p1 : list, p2 : list) -> tuple :
    return (p1[0] + p2[0]) / 2 , (p1[1] + p2[1]) / 2
    

# find center of arbitrary polygon - just a big average
def findCentroid(polygon : list) :
    x_list = [vertex [0] for vertex in polygon]
    y_list = [vertex [1] for vertex in polygon]
    num_sides = len(polygon)
    x = sum(x_list) / num_sides
    y = sum(y_list) / num_sides
    return(x, y)

# given a set of points, generate a triangle that contains all of thee
def generateBaseTriangle(points : list) -> list :
    # 1) create first triangle that contains all vertices 
    # begin by finding the extrema in all directions
    min_x = min(points, key = lambda p : p[0])[0]
    max_x = max(points, key = lambda p : p[0])[0]
    min_y = min(points, key = lambda p : p[1])[1]
    max_y = max(points, key = lambda p : p[1])[1]
    # put a box around all the points first (or rather, get the dimensions of such a box)
    # - if a triangle contanins this box, it'll contain every vertex
    width = max_x - min_x
    height = max_y - min_y
    # choose the longer of these dimensions - better to overestimate
    # triangle vertices will be determined based on this one 
    # - putting the vertices at least this far away gives us the desired containments
    # - multiply by 100 just to make absolutely sure it's big enough
    larger_dim = 100 * max(width, height)
    
    mid_x = (min_x + max_x) / 2
    mid_y = (min_y + max_y) / 2

    # NOTE : remember that in pygame, adding on the y-axis moves DOWN
    sup_tri_1 = (mid_x - larger_dim, mid_y - larger_dim)    # left and up from points
    sup_tri_2 = (mid_x + larger_dim, mid_y - larger_dim)    # straight across from prev - right and up from points
    sup_tri_3 = (mid_x, mid_y + larger_dim)                 # directly below middle 
    return sup_tri_1, sup_tri_2, sup_tri_3

# NOTE: we're ignoring what each point represents and just naivel creating the triangulation
# it feels easier to do this and then cull/merge only what we need than to try and only populate certain areas rn
def delaunay(points : list):
    # 1) GENERATE BASE CASE
    # we start with an "infinitely" large triangle - in practice it just contains every relevant vertex
    # this is essentially our base case, since this is a valid delaunay triangulation
    max_triangle = generateBaseTriangle(points)
    triangles = [max_triangle]

    # 2) ADD POINTS INTO TRIANGULATION
    # we continually add point after point to the triangulation, delaunay-ifying the new
    # complete graph each time. this is induction :)
    for point in points:
        # triangles that are invalidated by the insertion of the new point
        bad_triangles = []

        # 2-A) CHECK HOW NEW POINT AFFECTS TRIANGULATION
        # every iteration of this loop, a point is inserted into the triangulation
        # the insertion of a new point invalidates certain triangles, in particular
        for triangle in triangles:
            # check if new point lies //INSIDE// the circumcircle of the triangle
            # - if it is, it's gonna get popped
            # NOTE: don't think about the base case when trying to visualize why this makes sense
            # this comes into play with inserting points into nontrivial triangulations
            if inCircle(point, generateCircumcircle(triangle)):
                bad_triangles.append(triangle)

        # remove the bad triangles from the list
        # these 'bad' will potentially be part of the new triangulation
        edges = []
        for triangle in bad_triangles:
            triangles.remove(triangle)
            # check each edge of the triangle we just removed
            for i in range(3):
                edge = (triangle[i], triangle[(i + 1) % 3])
                if edge in edges:                   # duplicates
                    edges.remove(edge)
                elif (edge[1], edge[0]) in edges:   # duplicate stored differentlys
                    edges.remove((edge[1], edge[0]))
                else:                               # if edge isn't marked, mark it
                    edges.append(edge)

        # use the endpoints of those edges we just identified, along with the point we just inserted
        # to update the triangulation
        for edge in edges:
            triangles.append([edge[0], edge[1], point])

    # 2-B) FILTER OUTER TRIANGLES 
    # for t in triangles :    # loop over the whole triangulation
    #     rm_flag = False
    #     for v in t :        # loop over the vertices in a given triangle
    #         # eliminate triangles that share a vertex with the base triangle (and haven't already been removed)
    #         if v in max_triangle and t in triangles:
    #             rm_flag = True
        
    #     # we only want to remove if at least ONE of the vertices in this triangle is in the base
    #     if rm_flag :
    #         triangles.remove(t)

    filtered = []
    for t in triangles:     # loop over whole triangulation
        valid = True
        for v in t:         # loop over vertices in given triangle
            if v in max_triangle:   
                valid = False
                break
        if valid:
            filtered.append(t)
    triangles = filtered

    return triangles

# given three "consecutive" vertices calculate their cross product
# pick an arbitrary vertex on a polygon - draw a 
def cross_prod(origin, a, b):
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

# http://www.sunshine2k.de/coding/java/Polygon/Convex/polygon.htm
# https://stackoverflow.com/questions/8668548/how-to-check-if-polygon-is-convex
# ^ this phrased it nicely - we are walking around a polygon and making sure it's always the same direction
# we do this by picking looping over each vertex
# - for each one draw a vector to the next vertex, and another vector to the following one
# - taking the cross product of these for every possible origin will tell us if it is convex or not
def isConvex(polygon : list): 
    # trivial   
    n = len(polygon)
    if n < 4:
        return True

    sign = None
    for i in range(n): # loop over vertices, picking each one as our origin and drawing those vectors
        o, a, b = polygon[i], polygon[(i + 1) % n], polygon[(i + 2) % n]
        cross_product = cross_prod(o, a, b)
        if cross_product != 0:
            curr_sign = cross_product > 0
            if sign is None:
                sign = curr_sign
            elif sign != curr_sign: # if we ever change direction on our walk
                return False

    return True

# 3) MERGE THE TRIANGLES IN THE TRIANGLUATION THAT WILL STILL MAINTAIN CONVEXITY
# NOTE : we pass in the original edges of the environment to exclude them from the merging process
def mergeTriangles(triangles : list, original_edges):
    merged = []
    # keep track of triangles that have already been merged - set makes duplicates easier
    skip_indices = set()

    for i in range(len(triangles)):
        if i in skip_indices:
            continue
        
        t1 = triangles[i]
        merged_poly = None
        
        # compare this triangle to every SUBSEQUENT (saves time) triangle in the triangulation
        for j in range(i + 1, len(triangles)):
            if j in skip_indices:
                continue

            t2 = triangles[j]

            # determine if these two triangles share an edge
            shared = []
            t1_edges = [(t1[0], t1[1]), (t1[1], t1[2]), (t1[2], t1[0])]
            t2_edges = [(t2[0], t2[1]), (t2[1], t2[2]), (t2[2], t2[0])]

            for edge1 in t1_edges:
                for edge2 in t2_edges:
                    if edge1 == edge2 or edge1 == edge2[::-1]:
                        shared.append(edge1)

            # IF THEY DO
            if len(shared) == 1:
                shared = shared[0]
                # surprise tool
                if shared in original_edges or shared[::-1] in original_edges:
                    continue
                # joined in holy matrimony
                unique_points = list(set(t1 + t2) - set(shared))
                merged_poly = [shared[0], unique_points[0], shared[1], unique_points[1]]
                if isConvex(merged_poly) :
                    skip_indices.add(j)
                    # STOPs
                    break
                else :  # no shared edges found - move on
                    merged_poly = None

        if merged_poly :
            merged.append(merged_poly)
        else :
            merged.append(t1)

    return merged