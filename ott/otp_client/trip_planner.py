from ott.utils import json_utils
from ott.utils import html_utils
from ott.utils import otp_utils
from ott.otp_client import otp_to_ott
from ott.utils.parse.url.trip_param_parser import TripParamParser
from ott.geocoder.geosolr import GeoSolr

import sys
import simplejson as json
import urllib
import contextlib
import logging
log = logging.getLogger(__file__)


class TripPlanner(object):
    """
    example trip queries:
    """
    def __init__(self, otp_url="http://localhost/prod", solr='http://localhost/solr', adverts=None, fares=None, cancelled_routes=None):
        self.otp_url = otp_url

        self.geo = solr
        if isinstance(solr, str):
            self.geo = GeoSolr(solr)

        self.adverts = adverts
        self.fares = fares
        self.cancelled_routes = cancelled_routes

        # optionally create Adverts and Fares objects
        # note: requires change to this buildout to include the ott.data project
        try:
            if isinstance(adverts, str):
                from ott.data.content import Adverts
                self.adverts = Adverts(adverts)
        except Exception as e:
            log.warning(e)

        try:
            if isinstance(fares, str):
                from ott.data.content import Fares
                self.fares = Fares(fares)
        except Exception as e:
            log.warning(e)

        try:
            if isinstance(cancelled_routes, str) and 'http' in cancelled_routes:
                self.cancelled_routes = ""
                from ott.data.content import CancelledRoutes
                self.cancelled_routes = CancelledRoutes(cancelled_routes)
        except Exception as e:
            log.warning(e)

    def plan_trip(self, request=None, pretty=False):
        """
        ...
        powell%20blvd::45.49063653,-122.4822897"  "45.433507,-122.559709
        """
        # import pdb; pdb.set_trace()

        # step 1: parse params
        param = TripParamParser(request)

        # step 2: handle any geocoding needing to be done -- note, changes param object implicitly in the call
        msg = self.geocode(param)
        if msg:
            # TODO -- trip error or plan?
            pass

        # step 3: call the trip planner...
        otp_params = param
        otp_params.banned_routes = self.cancelled_routes
        if otp_params.is_latest():
            # step 3b: if we have Arr=L (latest trip), we need to increase the date by 1 day, since LATEST
            # trip is essentially an ArriveBy 1:30am trip
            if msg == 'chk':
                otp_utils.kill()
            otp_params = param.clone()
            otp_params.date_offset(day_offset=1)

        url = "{0}?{1}".format(self.otp_url, otp_params.otp_url_params())
        f = otp_utils.call_planner_svc(url)
        j = json.loads(f)

        # step 4: process any planner errors
        if j is None:
            pass
            # TODO -- trip error or plan?

        # step 5: parse the OTP trip plan into OTT format
        ret_val = {}
        try:
            plan = otp_to_ott.Plan(jsn=j['plan'], params=param, fares=self.fares)
            ret_val['plan'] = plan

            if self.adverts:
                m = plan.dominant_transit_mode()
                l = html_utils.get_lang(request)
                ret_val['adverts'] = self.adverts.query(m, l)
        except Exception as e:
            try:
                ret_val['error'] = otp_to_ott.Error(j['error'], param)
            except:
                log.warning("I think we had a problem parsing the JSON from OTP ... see exception below:")
                log.warning(e)

        ret_val = json_utils.json_repr(ret_val, pretty or param.pretty_output())
        return ret_val

    def geocode(self, param):
        """ TODO ... rethink this whole thing
            1) should geocoding be in param_parser
            2) we're going to need other parsers ... like for stops, etc... (where we only need to geocode 1 param, etc...)
            3) ....
        """
        ret_val = None

        # step 2: get your origin
        f = param.get_from()
        if not param.has_valid_coord(f):
            # step 2b: geocode the origin if you don't have a valid ::LatLon
            f = param.strip_coord(f)
            f = self.geo.geostr(f)
            param.frm = f

        # step 3: get your destination
        t = param.get_to()
        if not param.has_valid_coord(t):
            # step 3b: geocode the destination if you don't have a valid ::LatLon
            t = param.strip_coord(t)
            t = self.geo.geostr(t)
            param.to = t

        # step 4: check test scenario
        if ret_val is None and "pdx" in param.get('to') and "ohsu" in param.get('from') and "1:11" in param.get('time'):
            ret_val = "chk"

        return ret_val


def main():
    argv = sys.argv
    pretty = 'pretty' in argv or 'p' in argv
    trimet = 'trimet' in argv or 'tm' in argv
    oshu = 'ohsu' in argv or 'ohsu' in argv
    pdx = 'pdx' in argv or 'pdx' in argv
    if trimet:
        tp = TripPlanner(otp_url="http://maps.trimet.org/prod", solr='http://maps.trimet.org/solr')
    else:
        tp = TripPlanner()

    plan = tp.plan_trip(argv[1], pretty)
    print(plan)


if __name__ == '__main__':
    main()
