from ott.utils import object_utils
from ott.utils import otp_utils

from .base import Base

import logging
log = logging.getLogger(__file__)


class Routes(Base):
    """
    OpenTripPlanner's (OTP's) Transit Index (TI) is a GET web service that will return route, stop and schedule data from
    the OTP graph. The problem is that the TI cannot deal with date-based GTFS data.  Further, I would (strongly) argue
    that the TI is way out of OTP's scope architecturally.

    This call provides the route query services from gtfsdb as an alternate to OTP.

    The Routes class will deal with the following TI services:
      - ALL ROUTES   - https://<domain & port>/otp/routers/default/index/routes
      - SINGLE ROUTE - https://<domain & port>/otp/routers/default/index/route/<route_id>
      - STOP's ROUTE - https://<domain & port>/otp/routers/default/index/stops/TriMet:<route_id>/routes
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

        http://localhost:54445/ti/stops/TriMet:2/routes
        STOP's ROUTES RESPONSE:
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
        # import pdb; pdb.set_trace()
        if date:
            from gtfsdb import RouteStop
            routes = RouteStop.unique_routes_at_stop(session, stop_id=stop_id, agency_id=agency_id, date=date)
        else:
            from gtfsdb import CurrentRouteStops
            routes = CurrentRouteStops.unique_routes_at_stop(session, stop_id=stop_id, agency_id=agency_id)

        ret_val = cls._route_list_from_gtfsdb_orm_list(routes, agency_id)
        return ret_val

    @classmethod
    def route_list_factory(cls, session, date=None, agency_id=None):
        """
        :return a list of all route(s) for a given agency
        :note supplying a 'date' object will be *slower*, as it won't use the pre-calculated CurrentRoutes table

        http://localhost:54445/ti/routes
        http://localhost:54445/ti/routes?date=3-3-2019

        ROUTE LIST RESPONSE:
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
        """
        from gtfsdb import CurrentRoutes
        routes = CurrentRoutes.query_active_routes(session, date)
        ret_val = cls._route_list_from_gtfsdb_orm_list(routes, agency_id)
        return ret_val

    @classmethod
    def route_factory(cls, session, route_id, agency_id=None):
        """
        factory to generate a Route obj from a queried gtfsdb route

        http://localhost:54445/ti/routes/TriMet:18
        ROUTE RESPONSE (DETAILED)
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
        ret_val = None
        try:
            from .agency import Agency
            from gtfsdb import Route
            r = Route.query_route(session, route_id)
            agency = Agency().from_gtfsdb_factory(r.agency)
            route = cls._route_from_gtfsdb_orm(r, agency_id)
            route.agency = agency.__dict__
            ret_val = route.__dict__
        except Exception as e:
            log.warning(e)
        return ret_val

    @classmethod
    def _route_list_from_gtfsdb_orm_list(cls, gtfsdb_route_list, agency_id=None):
        """ input gtfsdb list, output Route obj list """
        ret_val = []
        for r in gtfsdb_route_list:
            route = cls._route_from_gtfsdb_orm(r, agency_id)
            ret_val.append(route.__dict__)
        return ret_val

    @classmethod
    def _route_from_gtfsdb_orm(cls, r, agency_id=None):
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

            otp_route_id = otp_utils.make_otp_id(route_id, agency_id)
            cfg = {'agencyName': agency_name, 'id': otp_route_id,
                   'shortName': short_name, 'longName': long_name,
                   'mode': mode, 'color': color, 'sortOrder': i+1}
            r = Routes(cfg)
            ret_val.append(r.__dict__)
        return ret_val
