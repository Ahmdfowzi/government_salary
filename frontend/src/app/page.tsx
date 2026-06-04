import { redirect } from "next/navigation";

// Root sends users into the Government Payroll module.
export default function Home() {
  redirect("/government-payroll");
}
