import base64
import xml.dom.minidom
from twisted.web.client import getPage
from twisted.internet import defer
from release.platforms import buildbot2bouncer

PRODUCT_INSTALLER, PRODUCT_COMPLETE_MAR, PRODUCT_PARTIAL_MAR = range(3)


def generateBouncerProduct(bouncerProductName, version, oldVersion=None,
                           productType=PRODUCT_INSTALLER):
    assert productType in (PRODUCT_INSTALLER, PRODUCT_COMPLETE_MAR,
                           PRODUCT_PARTIAL_MAR)
    ret = None

    if productType == PRODUCT_INSTALLER:
        ret = '%s-%s' % (bouncerProductName, version)
    elif productType == PRODUCT_COMPLETE_MAR:
        ret = '%s-%s-Complete' % (bouncerProductName, version)
    elif productType == PRODUCT_PARTIAL_MAR:
        assert oldVersion, "oldVersion paramter is required for partial MARs"
        ret = '%s-%s-Partial-%s' % (bouncerProductName, version, oldVersion)

    return ret


def getTuxedoUptakeUrl(tuxedoServerUrl, bouncerProductName, os):
    return '%s/uptake/?product=%s&os=%s' % (tuxedoServerUrl,
                                            bouncerProductName, os)


def get_product_uptake(tuxedoServerUrl, bouncerProductName, os,
                       timeout=30, username=None, password=None):
    d = defer.succeed(None)

    def getTuxedoPage(_):
        url = getTuxedoUptakeUrl(tuxedoServerUrl, bouncerProductName, os)
        if username and password:
            basicAuth = base64.encodestring('%s:%s' % (username, password))
            return getPage(url,
                           headers={'Authorization':
                                    'Basic %s' % basicAuth.strip()},
                           timeout=timeout)
        else:
            return getPage(url, timeout=timeout)

    def calculateUptake(page):
        doc = xml.dom.minidom.parseString(page)
        uptake_values = []

        for element in doc.getElementsByTagName('available'):
            for node in element.childNodes:
                if node.nodeType == xml.dom.minidom.Node.TEXT_NODE and \
                  node.data.isdigit():
                    uptake_values.append(int(node.data))
        if not uptake_values:
            uptake_values = [0]
        return min(uptake_values)

    d.addCallback(getTuxedoPage)
    d.addCallback(calculateUptake)
    return d


def get_release_uptake(tuxedoServerUrl, bouncerProductName, version,
                       platforms, oldVersion=None, checkMARs=True,
                       username=None, password=None):
    assert isinstance(platforms, (list, tuple))
    bouncerProduct = generateBouncerProduct(bouncerProductName, version)
    bouncerCompleteMARProduct = generateBouncerProduct(
        bouncerProductName,
        version,
        productType=PRODUCT_COMPLETE_MAR)
    bouncerPartialMARProduct = generateBouncerProduct(
        bouncerProductName, version,
        oldVersion,
        productType=PRODUCT_PARTIAL_MAR)
    dl = []

    for os in [buildbot2bouncer(x) for x in platforms]:
        dl.append(get_product_uptake(tuxedoServerUrl=tuxedoServerUrl,
                            bouncerProductName=bouncerProduct,
                            username=username, os=os,
                            password=password))
        if checkMARs:
            dl.append(get_product_uptake(
                tuxedoServerUrl=tuxedoServerUrl,
                os=os, bouncerProductName=bouncerCompleteMARProduct,
                username=username, password=password))
            if oldVersion:
                dl.append(get_product_uptake(
                    tuxedoServerUrl=tuxedoServerUrl, os=os,
                    bouncerProductName=bouncerPartialMARProduct,
                    username=username, password=password))

    def get_min(res):
        return min([int(x[1]) for x in res])

    dl = defer.DeferredList(dl, fireOnOneErrback=True)
    dl.addCallback(get_min)
    return dl
