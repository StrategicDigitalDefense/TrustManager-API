# Work to do

* documentation
* wrap at least /Trust and /Distrust in AuthZ
    * Probably also the PUT /Certificate and the POST /BatchJob
    * This means I'll need to make it either 
        * use Krb5 for AuthN and then lookup the groups
            * And does this mean retrieving the PAC from an AD TGT, or making an LDAP lookup? 
        * OR I will need to make it require a JWT from OAuth, and then check the roles
            * learning to OAuth-ify an app fills me with ph33r and intimidation
    * either way, it sounds difficult and intimidatiing
* switch from SQLite3 to instead a real database, like SQL Svr, Oracle, PostGres
* externalize configuration
    * This will be particularly important for things like database connection information, AuthZ allowed roes/groups, AuthZ configuration (server, relying-party secret, etc)

# Completed
* ~~GUI~~ 
    * ~~Decision: Native WPF/WinForms in PowerShell, or web GUI~~
    * Decided a Web GUI for now. May make a native Windows GUI some other time
* ~~batch job for Windows truststore~~
    * ~~I know you can distribute and manage truststore with Group Policy~~
    * ~~I know you can distribute Group Policy in ADMX files, which are XML-encoded collections of GPOs~~
    * ~~I need to see if I can figure out how to make an ADMX to distribute a GPO that manages trust, providing all the root CAs in the database maked trusted~~
* ~~Documentation how to consume/operationalize the truststores~~
* ~~instructions to run inside a WSGI server, instead of the built-in development webserver~~
    * ~~It's now running under waitress.serve. That was easy.~~ 
* ~~Dockerfile to package the app + WSGI server + Python together~~

