import { redirect } from "next/navigation";

/** Landing page redirects to dashboard or login. */
export default function Home() {
  redirect("/dashboard");
}
