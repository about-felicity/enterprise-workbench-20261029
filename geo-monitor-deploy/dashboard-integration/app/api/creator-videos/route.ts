import { getVideos, postVideos } from "../videoProxy";

export function GET(request: Request) {
  return getVideos(request);
}

export function POST(request: Request) {
  return postVideos(request);
}
