import { getVideos, postVideos } from "../../videoProxy";

export function GET(request: Request) {
  return getVideos(request, "paid-media-videos");
}

export function POST(request: Request) {
  return postVideos(request, "paid-media-videos");
}
