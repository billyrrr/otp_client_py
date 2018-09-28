from ott.utils import object_utils
from ott.utils import otp_utils
from ott.utils import json_utils

from .base import Base

import logging
log = logging.getLogger(__file__)


class Routes(Base):
    """
    ROUTE LIST:
    https://<domain & port>/otp/routers/default/index/routes
    [
        {
            "id": "TriMet:54",
            "agencyName": "TriMet",
            "shortName": "54",
            "longName": "Beaverton-Hillsdale Hwy",
            "mode": "BUS"
        },
        {

            "id": "TriMet:193",
            "longName": "Portland Streetcar - NS Line",
            "mode": "TRAM" or "GONDOLA" or "RAIL" or ...
            "color": "84BD00",
            "agencyName": "Portland Streetcar"

        }
    ]

    STOP's ROUTES:
    https://<domain & port>/otp/routers/default/index/stops/TriMet:5516/routes
    [
      {
        "id": "TriMet:10",
        "shortName": "10",
        "longName": "Harold St",
        "mode": "BUS",
        "agencyName": "TriMet"
      }
    ]
    """
    def __init__(self, args={}):
        super(Routes, self).__init__(args)
        object_utils.safe_set_from_dict(self, 'mode', args)
        object_utils.safe_set_from_dict(self, 'type', args)
        object_utils.safe_set_from_dict(self, 'longName', args)
        object_utils.safe_set_from_dict(self, 'shortName', args, always_cpy=False)

        object_utils.safe_set_from_dict(self, 'sortOrder', args, always_cpy=False)
        if object_utils.safe_get(self, 'sortOrder'): self.sortOrderSet = True

        object_utils.safe_set_from_dict(self, 'url', args, always_cpy=False)
        object_utils.safe_set_from_dict(self, 'color', args, always_cpy=False)
        object_utils.safe_set_from_dict(self, 'textColor', args, always_cpy=False)

    @classmethod
    def stop_routes_factory(cls, session, stop_id, date=None, agency_id=None):
        """
        :return a list of all route(s) serving a given stop
        """
        from ott.data.dao.stop_dao import StopDao
        from ott.data.dao.route_dao import RouteListDao
        s = StopDao.query_orm_for_stop(session, stop_id, detailed=False) # detailed here will bring amenities
        routes = RouteListDao.filter_active_routes(s.routes, date=date)
        ret_val = cls._route_list_from_gtfsdb_list(routes, agency_id)
        return ret_val

    @classmethod
    def route_list_factory(cls, session, date=None, agency_id=None):
        """
        :return a list of all route(s) for a given agency
        """
        from ott.data.dao.route_dao import RouteListDao
        routes = RouteListDao.active_routes(session, date=date)
        ret_val = cls._route_list_from_gtfsdb_list(routes, agency_id)
        return ret_val

    @classmethod
    def route_factory(cls, session, route_id, agency_id=None):
        """
        factory to generate a Route obj from a queried gtfsdb route

        FYI, this is what that stupid OTP TI returns
        https://trimet-otp.conveyal.com/otp/routers/default/index/routes/TriMet:18
        {
            "id": "TriMet:18",
            "agency": {
                "id": "TRIMET",
                "name": "TriMet",
                "url": "http://trimet.org/",
                "timezone": "America/Los_Angeles",
                "lang": "en",
                "phone": "503-238-RIDE",
                "fareUrl": "http://trimet.org/fares/"
            },
            "shortName": "18",
            "longName": "Hillside",
            "type": 3,
            "url": "http://trimet.org//schedules/r018.htm",
            "routeBikesAllowed": 0,
            "bikesAllowed": 0,
            "sortOrder": 2300,
            "sortOrderSet": true
        }
        """
        from gtfsdb import Route
        r = session.query(Route).filter(Route.route_id == route_id).one()
        route = cls._route_from_gtfsdb(r, agency_id)

        class Agency():
            @classmethod
            def from_gtfsdb_factory(cls, agency):
                """
                {
                  'agency_id': u'TRIMET'
                  'agency_name': u'TriMet'
                  'agency_url': u'http://trimet.org/'
                  'agency_fare_url': u'http://trimet.org/fares/',
                  'agency_timezone': u'America/Los_Angeles',
                  'agency_lang': u'en',
                  'agency_email': u'customerservice@trimet.org'
                }
                """
                #import pdb; pdb.set_trace()
                a = Agency()
                a.id = agency.agency_id
                a.name = agency.agency_name
                a.url = agency.agency_url
                a.fareUrl = agency.agency_fare_url
                a.timezone = agency.agency_timezone
                a.lang = agency.agency_lang
                a.phone = agency.agency_phone
                return a

        route.agency = Agency().from_gtfsdb_factory(r.agency).__dict__

        ret_val = route.__dict__
        return ret_val

    @classmethod
    def _route_list_from_gtfsdb_list(cls, gtfsdb_route_list, agency_id=None):
        """ input gtfsdb list, output Route obj list """
        ret_val = []
        for r in gtfsdb_route_list:
            route = cls._route_from_gtfsdb(r, agency_id)
            ret_val.append(route.__dict__)
        return ret_val

    @classmethod
    def _route_from_gtfsdb(cls, r, agency_id=None):
        """ factory to genereate a Route obj from a queried gtfsdb route """
        agency = agency_id if agency_id else r.agency_id
        otp_route_id = otp_utils.make_otp_id(r.route_id, agency)
        cfg = {
            'agencyName': r.agency.agency_name, 'id': otp_route_id,
            'longName': r.route_long_name, 'shortName': r.route_short_name,
            'mode': r.type.otp_type, 'type': r.type.route_type,
            'sortOrder': r.route_sort_order,
            'color': r.route_color, 'textColor': r.route_text_color
        }
        ret_val = Routes(cfg)
        return ret_val


    @classmethod
    def mock(cls, agency_id="MOCK"):
        """
        """
        ret_val = []

        for i in range(50):
            agency_name = agency_id
            route_id = str(i+1)
            short_name = str(route_id) if i % 2 else None
            long_name = "{}-{}".format(i+1, agency_id)
            color = "Ox{:02}{:02}{:02}".format(i+3, i*2, i+17)
            mode = "TRAM" if i % 3 else "BUS"

            otp_route_id = otp_utils.make_otp_route_id(route_id, agency_id)
            cfg = {'agencyName': agency_name, 'id': otp_route_id,
                   'shortName': short_name, 'longName': long_name,
                   'mode': mode, 'color': color, 'sortOrder': i+1}
            r = Routes(cfg)
            ret_val.append(r.__dict__)

        return ret_val
