import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { Spinner } from "@/components/ui/kit";
import { RequireStaff, RequirePortal } from "@/lib/auth";
import PublicLayout from "@/components/public/Layout";
import Home from "@/pages/public/Home";
import { ServicesPage, ServiceDetail, IndustriesPage, IndustryDetail, ProductsPage, ClientsPage, GalleryPage, AboutPage, SafetyQualityPage, AmcPage, TownPage, LegalPage, NotFound } from "@/pages/public/Content";
import { ProjectsPage, ProjectDetail } from "@/pages/public/Projects";
import { ToolsHub, ToolPage, StaffToolsHub } from "@/pages/public/Tools";
import { ResourcesPage, InsightsPage, InsightDetail, GuidePage } from "@/pages/public/Resources";
import { ContactPage, GetQuotePage, BookSurveyPage, BillReviewPage, TendersPage, EmergencyPage, CareersPage, VendorRegistrationPage, AssetPage } from "@/pages/public/Forms";
import { LoginPage, ForgotPage, SetPasswordPage } from "@/pages/Auth";

// Staff app and portals load separately, so the public website stays light.
const ErpLayout = lazy(() => import("@/erp/Layout"));
const EntityListPage = lazy(() => import("@/erp/EntityList"));
const EntityDetailPage = lazy(() => import("@/erp/EntityDetail"));
const Dashboard = lazy(() => import("@/erp/pages/Home").then((m) => ({ default: m.Dashboard })));
const Approvals = lazy(() => import("@/erp/pages/Home").then((m) => ({ default: m.Approvals })));
const CalendarPage = lazy(() => import("@/erp/pages/Home").then((m) => ({ default: m.CalendarPage })));
const Ceo = lazy(() => import("@/erp/pages/Ceo"));
const Pipeline = lazy(() => import("@/erp/pages/Crm").then((m) => ({ default: m.Pipeline })));
const Marketing = lazy(() => import("@/erp/pages/Crm").then((m) => ({ default: m.Marketing })));
const Stores = lazy(() => import("@/erp/pages/Ops").then((m) => ({ default: m.Stores })));
const ServiceDesk = lazy(() => import("@/erp/pages/Ops").then((m) => ({ default: m.ServiceDesk })));
const Finance = lazy(() => import("@/erp/pages/Ops").then((m) => ({ default: m.Finance })));
const ReportsHome = lazy(() => import("@/erp/pages/Reports").then((m) => ({ default: m.ReportsHome })));
const ReportView = lazy(() => import("@/erp/pages/Reports").then((m) => ({ default: m.ReportView })));
const SettingsPage = lazy(() => import("@/erp/pages/Admin").then((m) => ({ default: m.SettingsPage })));
const UsersPage = lazy(() => import("@/erp/pages/Admin").then((m) => ({ default: m.UsersPage })));
const AuditPage = lazy(() => import("@/erp/pages/Admin").then((m) => ({ default: m.AuditPage })));
const WebsiteEditor = lazy(() => import("@/erp/pages/Admin").then((m) => ({ default: m.WebsiteEditor })));
const Me = lazy(() => import("@/erp/pages/Me"));
const Vault = lazy(() => import("@/erp/pages/Me").then((m) => ({ default: m.Vault })));
const P = (name) => lazy(() => import("@/portal/Portal").then((m) => ({ default: m[name] })));
const PortalLayout = P("PortalLayout");
const ClientHome = P("ClientHome");
const ClientProjects = P("ClientProjects");
const ClientProject = P("ClientProject");
const ClientBills = P("ClientBills");
const ClientService = P("ClientService");
const ClientNew = P("ClientNew");
const ConsultantHome = P("ConsultantHome");
const VendorHome = P("VendorHome");
const SubcontractorHome = P("SubcontractorHome");
const PartnerHome = P("PartnerHome");

function Wait() {
  return <div className="flex min-h-[50vh] items-center justify-center"><Spinner label="Loading" /></div>;
}
function Go({ to }) {
  const p = useParams();
  return <Navigate to={to.replace(/:(\w+)/g, (_, k) => p[k])} replace />;
}

export default function App() {
  return (
    <Suspense fallback={<Wait />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<Home />} />
          <Route path="services" element={<ServicesPage />} />
          <Route path="services/:slug" element={<ServiceDetail />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="industries" element={<IndustriesPage />} />
          <Route path="industries/:slug" element={<IndustryDetail />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:slug" element={<ProjectDetail />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="gallery" element={<GalleryPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="safety-quality" element={<SafetyQualityPage />} />
          <Route path="amc" element={<AmcPage />} />
          <Route path="tools" element={<ToolsHub />} />
          <Route path="tools/:slug" element={<ToolPage />} />
          <Route path="resources" element={<ResourcesPage />} />
          <Route path="guides/:slug" element={<GuidePage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="insights/:slug" element={<InsightDetail />} />
          <Route path="contact" element={<ContactPage />} />
          <Route path="get-quote" element={<GetQuotePage />} />
          <Route path="book-survey" element={<BookSurveyPage />} />
          <Route path="bill-review" element={<BillReviewPage />} />
          <Route path="tenders" element={<TendersPage />} />
          <Route path="emergency" element={<EmergencyPage />} />
          <Route path="careers" element={<CareersPage />} />
          <Route path="vendor-registration" element={<VendorRegistrationPage />} />
          <Route path="asset/:token" element={<AssetPage />} />
          <Route path="electrical-contractors-in/:slug" element={<TownPage />} />
          <Route path="privacy" element={<LegalPage kind="privacy" />} />
          <Route path="terms" element={<LegalPage kind="terms" />} />
          <Route path="cookies" element={<LegalPage kind="cookies" />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route path="login" element={<LoginPage />} />
        <Route path="erp/login" element={<LoginPage staff />} />
        <Route path="forgot-password" element={<ForgotPage />} />
        <Route path="set-password" element={<SetPasswordPage />} />

        <Route path="erp" element={<RequireStaff><ErpLayout /></RequireStaff>}>
          <Route index element={<Dashboard />} />
          <Route path="ceo" element={<Ceo />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="crm" element={<Pipeline />} />
          <Route path="marketing" element={<Marketing />} />
          <Route path="stores" element={<Stores />} />
          <Route path="service" element={<ServiceDesk />} />
          <Route path="finance" element={<Finance />} />
          <Route path="reports" element={<ReportsHome />} />
          <Route path="reports/:key" element={<ReportView />} />
          <Route path="tools" element={<StaffToolsHub />} />
          <Route path="tools/:slug" element={<ToolPage staff />} />
          <Route path="website" element={<WebsiteEditor />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="vault" element={<Vault />} />
          <Route path="me" element={<Me />} />
          <Route path="e/:key" element={<EntityListPage />} />
          <Route path="e/:key/:id" element={<EntityDetailPage />} />
          <Route path="projects/:id" element={<Go to="/erp/e/projects/:id" />} />
          <Route path="rfqs/:id/compare" element={<Go to="/erp/e/rfqs/:id" />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route element={<RequirePortal><PortalLayout /></RequirePortal>}>
          <Route path="client" element={<RequirePortal roles={["client"]}><ClientHome /></RequirePortal>} />
          <Route path="client/projects" element={<RequirePortal roles={["client"]}><ClientProjects /></RequirePortal>} />
          <Route path="client/projects/:id" element={<RequirePortal roles={["client"]}><ClientProject /></RequirePortal>} />
          <Route path="client/bills" element={<RequirePortal roles={["client"]}><ClientBills /></RequirePortal>} />
          <Route path="client/service" element={<RequirePortal roles={["client"]}><ClientService /></RequirePortal>} />
          <Route path="client/new" element={<RequirePortal roles={["client"]}><ClientNew /></RequirePortal>} />
          <Route path="consultant" element={<RequirePortal roles={["consultant"]}><ConsultantHome /></RequirePortal>} />
          <Route path="vendor" element={<RequirePortal roles={["vendor"]}><VendorHome /></RequirePortal>} />
          <Route path="subcontractor" element={<RequirePortal roles={["subcontractor"]}><SubcontractorHome /></RequirePortal>} />
          <Route path="partner" element={<RequirePortal roles={["partner"]}><PartnerHome /></RequirePortal>} />
        </Route>
      </Routes>
    </Suspense>
  );
}
