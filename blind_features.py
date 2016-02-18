#!/bin/python

"""
USAGE:
    blind_features.py <image>...
"""

__author__ = 'Stephen Zakrewsky'


import cv2
import docopt
import numpy as np


def spatial_edge_distribution2(img):
    lb = abs(cv2.Laplacian(img[:,:,0],cv2.CV_32F))
    lg = abs(cv2.Laplacian(img[:,:,1],cv2.CV_32F))
    lr = abs(cv2.Laplacian(img[:,:,2],cv2.CV_32F))
    L = (lb + lg + lr)/3
    L = cv2.resize(L, (100,100))
    L = L/np.sum(L)

    Y = np.sum(L, axis=1)
    X = np.sum(L, axis=0)
    wx = width_mass(X, 0.98)/100.0
    wy = width_mass(Y, 0.98)/100.0

    return 1 - wx*wy


def hue_count_feature(img, a=0.05):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(img, np.array([0, 255*0.2, 255*0.15], int), np.array([179, 255, 255*0.95], int))
    hist = cv2.calcHist([img], [0], mask, [20], [0, 179])
    N = hist > a*np.max(hist)
    return 20 - np.count_nonzero(N)


def blur_feature(img, thresh=5):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    dft = cv2.dft(np.float32(img), flags=cv2.DFT_COMPLEX_OUTPUT)
    mag = cv2.magnitude(dft[:,:,0], dft[:,:,1])
    C = np.count_nonzero(mag > thresh)
    return C/float(img.shape[0] * img.shape[1])


def blur_feature_tong_etal(img, thresh=35, MinZero=0.05):
    import pywt
    w = pywt.wavedec2(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 'haar', level=3)

    emap = [np.sqrt(w[i][0]**2 + w[i][1]**2 + w[i][2]**2) for i in range(1, len(w))]
    window_size_map = [2, 4, 8]
    emax = [np.zeros((int(e.shape[0]/float(s) + 0.5), int(e.shape[1]/float(s) + 0.5))) for e, s in zip(emap, window_size_map)]

    for e, s, m in zip(emap, window_size_map, emax):
        for y in range(0, int(e.shape[0]/float(s) + 0.5)):
            for x in range(0, int(e.shape[1]/float(s) + 0.5)):
                ep = e[y*s:y*s+s,x*s:x*s+s]
                m[y,x] = np.amax(ep)

    r1 = edge_point = np.logical_or(emax[0] > thresh, np.logical_or(emax[1] > thresh, emax[2] > thresh))
    r2 = ds_or_as = np.logical_and(edge_point, np.logical_and(emax[0] > emax[1], emax[1] > emax[2]))
    r3 = rs_or_gs = np.logical_and(edge_point, np.logical_and(emax[0] < emax[1], emax[1] < emax[2]))
    r4 = rs = np.logical_and(edge_point, np.logical_and(emax[1] > emax[0], emax[1] > emax[2]))
    r5 = more_likely = np.logical_and(np.logical_or(rs_or_gs, rs), emax[0] < thresh)

    N_edge = np.count_nonzero(r1)
    N_da = np.count_nonzero(r2)
    N_rg = np.count_nonzero(np.logical_or(r3, r4))
    N_brg = np.count_nonzero(r5)
    Per = float(N_da)/float(N_edge)
    unblured = Per > MinZero
    BlurExtent = float(N_brg)/float(N_rg)

    return BlurExtent


def contrast_feature(img):
    hb = cv2.calcHist([img], [0], None, [256], [0, 256]).ravel()
    hg = cv2.calcHist([img], [1], None, [256], [0, 256]).ravel()
    hr = cv2.calcHist([img], [2], None, [256], [0, 256]).ravel()
    hist = hb + hg + hr
    hist = hist/sum(hist)
    return width_center_mass(hist, 0.98)


def brightness_feature(img):
    img = np.float32(img)/255
    img = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
    return np.mean(img[:,:,0])


def width_center_mass(x, p):
    n = len(x)
    c = n/2
    center_mass = x[c]
    if center_mass >= p:
        return 1
    for i in range(1, c):
        center_mass += x[c-i]
        center_mass += x[c+i]
        if center_mass >= p:
            return 2*i+1
    return n


def width_mass(x, p):
    count = 1
    import scipy.ndimage
    c = int(scipy.ndimage.center_of_mass(x)[0] + 0.5)
    n = len(x)
    center_mass = x[c]
    if center_mass >= p:
        return count
    for i in range(1, max(c, n-c)):
        if c-i >= 0:
            center_mass += x[c-i]
            count += 1
        if c+i < n:
            center_mass += x[c+i]
            count += 1
        if center_mass >= p:
            return count
    return count


def get_image():
    import requests
    r = requests.get('https://openapi.etsy.com/v2/listings/175320841/images?api_key=6xlt7fqhid48yle9y2ig78k9')
    print r.json()


def mser_feature(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mser = cv2.MSER_create()
    regions = mser.detectRegions(img, None)
    return len(regions)


def saliency_feature(img):
    img_orig = img
    img = cv2.resize(img, (64, 64))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # import math
    # h = cv2.getOptimalDFTSize(img.shape[0])
    # w = cv2.getOptimalDFTSize(img.shape[1])
    # print "Resizing (%d, %d) to (%d, %d)" % (img.shape[0], img.shape[1], h, w)
    # h = (h - img.shape[0])/2.0
    # w = (w - img.shape[1])/2.0
    # img = cv2.copyMakeBorder(img, int(math.floor(h)), int(math.ceil(h)), int(math.floor(w)), int(math.ceil(w)), cv2.BORDER_CONSTANT, value=0)

    dft = cv2.dft(np.float32(img), flags=cv2.DFT_COMPLEX_OUTPUT)
    A, P = cv2.cartToPolar(dft[:,:,0], dft[:,:,1])
    L = cv2.log(A)
    h_n = (1./3**2)*np.ones((3,3))
    R = L - cv2.filter2D(L, -1, h_n)
    S = cv2.GaussianBlur(cv2.idft(np.dstack(cv2.polarToCart(cv2.exp(R), P)), flags=cv2.DFT_REAL_OUTPUT)**2, (0,0), 8)
    S = cv2.resize(cv2.normalize(S, None, 0, 1, cv2.NORM_MINMAX), (img_orig.shape[1],img_orig.shape[0]))

    # cv2.namedWindow('tmp1', cv2.WINDOW_NORMAL)
    # cv2.imshow('tmp1', img_orig)
    # cv2.namedWindow('tmp', cv2.WINDOW_NORMAL)
    # cv2.imshow('tmp', S)
    # cv2.waitKey()

    return S

def thirds_map_feature(img):
    h, w = img.shape[0], img.shape[1]
    htwidth = h/6.
    ht1 = h/3.
    ht2 = 2*h/3.
    wtwidth = w/6.
    wt1 = w/3.
    wt2 = 2*w/3.

    x = [0, wt1 - wtwidth/2, wt1 + wtwidth/2, wt2 - wtwidth/2, wt2 + wtwidth/2, w]
    y = [0, ht1 - htwidth/2, ht1 + htwidth/2, ht2 - htwidth/2, ht2 + htwidth/2, h]

    TM = np.zeros((5,5))
    S = saliency_feature(img)
    for j in range(0,5):
        for i in range(0,5):
            roi = S[y[j]:y[j+1],x[i]:x[i+1]]
            TM[j, i] = np.sum(roi)/(roi.shape[0]*roi.shape[1])
    TM = TM/np.sum(TM)

    # draw thirds lines
    # S[:,x[1]] = 1
    # S[:,x[2]] = 1
    # S[:,x[3]] = 1
    # S[:,x[4]] = 1
    # S[y[1],:] = 1
    # S[y[2],:] = 1
    # S[y[3],:] = 1
    # S[y[4],:] = 1

    # cv2.namedWindow('tmp1', cv2.WINDOW_NORMAL)
    # cv2.imshow('tmp1', img)
    # cv2.namedWindow('tmp2', cv2.WINDOW_NORMAL)
    # cv2.imshow('tmp2', S)
    # cv2.namedWindow('tmp3', cv2.WINDOW_NORMAL)
    # cv2.imshow('tmp3', TM)
    # cv2.waitKey()
    return TM.ravel()


if __name__ == '__main__':

    arguments = docopt.docopt(__doc__)
    for i in arguments['<image>']:
        img = cv2.imread(i)
        print i, spatial_edge_distribution2(img), hue_count_feature(img), blur_feature(img), \
            blur_feature_tong_etal(img), contrast_feature(img), brightness_feature(img), mser_feature(img), \
            thirds_map_feature(img)

print get_image()