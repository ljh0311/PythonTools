/** LTA DataMall Bus Arrival API response types */

export interface BusArrivalNextBus {
  OriginCode: string;
  DestinationCode: string;
  EstimatedArrival: string;
  Latitude?: string;
  Longitude?: string;
  VisitNumber?: string;
  Load?: string;
  Feature?: string;
}

export interface BusArrivalService {
  ServiceNo: string;
  Operator: string;
  NextBus: BusArrivalNextBus;
  NextBus2?: BusArrivalNextBus;
  NextBus3?: BusArrivalNextBus;
}

export interface BusArrivalResponse {
  BusStopCode: string;
  Services: BusArrivalService[];
}

/** LTA BusStops dataset (subset returned by our search API) */
export interface BusStopLookup {
  BusStopCode: string;
  RoadName: string;
  Description: string;
}

export interface BusStopSearchResponse {
  matches: BusStopLookup[];
}
